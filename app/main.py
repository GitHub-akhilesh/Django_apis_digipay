import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.utils.logging import setup_logging
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.deprecation import DeprecationMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.routers.v1.endpoints import router as v1_router
from app.routers.v1.agent import router as agent_router

# Initialize structured logging
setup_logging()
logger = logging.getLogger("digipay.main")

app = FastAPI(
    title="DigiPay API Gateway & Ledger Services",
    description="Enterprise API logs and ledgers transaction management system.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 1. Correlation Tracking - generates/propagates correlation UUIDs across downstream services
app.add_middleware(CorrelationIdMiddleware)

# 2. Rate Limiting - sheds loads early based on IP address prior to expensive authentication validation
app.add_middleware(RateLimitMiddleware)

# 3. Sunsetting & Deprecation Governance - monitors API lifespan rules and handles blockages/warnings
app.add_middleware(DeprecationMiddleware)

# 4. Authentication & Multi-Tenant Routing - verifies claims and populates active tenant context variables
app.add_middleware(AuthMiddleware)

# 5. CORS Middleware - closest to the client to intercept preflight OPTIONS requests
# Registered last to ensure it runs first (outermost middleware) to handle OPTIONS requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(v1_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")

# Serve Chat SDK and Demo UI static files
sdk_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk")
if os.path.exists(sdk_dir):
    app.mount("/sdk", StaticFiles(directory=sdk_dir, html=True), name="sdk")

@app.get("/", include_in_schema=False)
async def index_redirect():
    return RedirectResponse(url="/docs")

@app.on_event("startup")
async def startup_event():
    logger.info(f"DigiPay API Gateway starting up under {settings.ENV} environment...")
