import logging
import time
import uvicorn
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

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI Support Platform with Global Response Builder and Error Catalog.",
    version=settings.APP_VERSION
)

from api.routers.health import router as health_router
from api.routers.chat import router as chat_router
from api.routers.websocket import router as ws_router
from api.routers.observability import router as obs_router
from api.routers.admin import router as admin_router

# Include Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(obs_router)
app.include_router(admin_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=True)
