import logging
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from core.config import settings
from core.logger import configure_logging
from core.exceptions import AIPlatformException
from core.responses import ApiResponse
from monitoring.middleware import TracingMiddleware
from monitoring.metrics import record_http_request, record_http_latency
from auth.middleware import JWTAuthenticationMiddleware

# Initialize structured logging
configure_logging()
logger = logging.getLogger("ai_platform.main")
logger.info("Initializing DigiPay AI Platform (DAP) Platform Core...")

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Startup: report the resolved tool catalogue and seed the MongoDB RAG store.
    Shutdown: release the gateway connection pool and the Mongo client.

    Seeding is non-fatal — an unreachable MongoDB degrades FAQ retrieval to the
    in-memory index rather than preventing the service from starting.
    """
    from tools.catalog import catalog_summary

    summary = catalog_summary()
    logger.info(
        "Tool registry resolved: %s tools (%s read-only, %s state-changing) across domains %s",
        summary["totalTools"],
        summary["readOnlyTools"],
        summary["stateChangingTools"],
        list(summary["byDomain"]),
    )

    if settings.RAG_AUTO_SEED:
        try:
            from rag.ingest import ingest_service
            logger.info(f"RAG bootstrap: {await ingest_service.seed_knowledge_base()}")
        except Exception as e:
            logger.warning(f"RAG bootstrap skipped: {e}")

    yield

    from gateway.client import GatewayClient
    from rag.mongo_store import mongo_vector_store

    await GatewayClient.close()
    await mongo_vector_store.close()


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI Support Platform with Global Response Builder and Error Catalog.",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

from api.routers.health import router as health_router
from api.routers.chat import router as chat_router
from api.routers.websocket import router as ws_router
from api.routers.observability import router as obs_router
from api.routers.admin import router as admin_router
from api.routers.knowledge import router as knowledge_router

# Include Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(obs_router)
app.include_router(admin_router)
app.include_router(knowledge_router)

# ---------------------------------------------------------------------------
# Document the legacy DigiPay API alongside this service's own endpoints.
#
# The legacy service (app/main.py) stays deployed separately on its original
# URLs — nothing a frontend calls changes. Merging only its OpenAPI schema means
# one Swagger UI shows both APIs, with each legacy path carrying a `servers`
# override so "Try it out" reaches the legacy service.
# ---------------------------------------------------------------------------
from api.openapi_aggregate import merge_legacy_openapi

_fastapi_openapi = app.openapi


def openapi_with_legacy():
    """FastAPI's schema plus the legacy service's paths."""
    if getattr(app, "_openapi_merged", False):
        return app.openapi_schema
    schema = merge_legacy_openapi(_fastapi_openapi())
    app.openapi_schema = schema
    app._openapi_merged = True
    return schema


app.openapi = openapi_with_legacy

# NOTE: CORS is registered at the very BOTTOM of this file, not here.
# Starlette's add_middleware prepends, so the LAST registration is the OUTERMOST
# layer. CORS must be outermost to answer preflight OPTIONS requests before the
# JWT middleware sees them. See the comment at the registration site.

# Exception Handler using Global Response Builder ApiResponse.error()
@app.exception_handler(AIPlatformException)
async def dap_exception_handler(request: Request, exc: AIPlatformException) -> JSONResponse:
    logger.error(
        f"API Error occurred: {exc.error_code} | Dev Msg: {exc.developer_message} | Trace: {exc.trace_id}",
        exc_info=True
    )
    return ApiResponse.respond_error(
        error_code=exc.error_code,
        message=str(exc),
        developer_message=exc.developer_message,
        details=exc.details,
        status_code=exc.status_code,
        headers={"X-Trace-ID": exc.trace_id} if exc.trace_id else None
    )

# Middlewares (Reverse order processing)
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    if request.url.path != "/metrics":
        record_http_request(request.method, request.url.path, response.status_code)
        record_http_latency(request.url.path, duration)
        
    return response

app.add_middleware(JWTAuthenticationMiddleware)
app.add_middleware(TracingMiddleware)

# ---------------------------------------------------------------------------
# CORS — registered LAST on purpose, so it is the OUTERMOST middleware.
#
# Starlette's add_middleware prepends: the last registration wraps everything
# above. CORS has to be outermost because a browser preflight is an OPTIONS
# request that carries NO Authorization header by definition. Registered inside
# the JWT middleware, that preflight was answered with 401 and, critically,
# WITHOUT any Access-Control-Allow-* headers — which the browser surfaces as an
# opaque "CORS error" on every cross-origin call, e.g. the React dev server on
# :5173 calling POST /api/v1/chat here.
#
# app/main.py already does it this way; this service did not, hence the bug.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID", "X-Correlation-ID", "X-Request-ID"],
)

@app.get("/metrics")
async def metrics():
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return PlainTextResponse(
            "# HELP http_requests_total Mock metrics active. Install prometheus_client to expose metrics.\n",
            media_type="text/plain"
        )

if __name__ == "__main__":
    # Bind to settings.HOST (0.0.0.0 by default) rather than a hard-coded
    # 127.0.0.1: a container listening only on loopback is unreachable from
    # outside it. Auto-reload is a local-development convenience and must stay
    # off elsewhere — it doubles memory and restarts on any file touch.
    is_local = settings.ENVIRONMENT.lower() in ("local", "dev", "development")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=is_local,
    )
