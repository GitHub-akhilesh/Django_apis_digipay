"""
Application Configuration

This module acts as the Single Source of Truth (SSOT)
for all application configurations.

Never use:
    os.getenv()

outside this file.

Every module should import:

from core.config import settings
"""

import os
from functools import lru_cache
from typing import Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root — two levels up from ai_platform/core/config.py.
#
# Env files MUST be resolved absolutely. They previously used bare relative
# names, which pydantic resolves against the process working directory; because
# this service is started from `ai_platform/` while the env files live at the
# repository root, none of them were ever loaded. Everything appeared to work
# only because the defaults below happen to match .env.local, so any setting
# changed in an env file was silently ignored.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AppSettings(BaseSettings):
    """
    Application-specific configurations.
    """
    APP_NAME: str = "DigiPay AI Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(
        default="local",
        description="Application Environment",
    )
    ENV: str = "LOCAL"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8001


class GatewaySettings(BaseSettings):
    """
    API Gateway endpoints and relative routes.
    """
    # DigiPay Spring Boot gateway-service base URL.
    #
    #   production   https://digipayapi.csccloud.in
    #   uat / local  https://digipayapiuat.csccloud.in
    #
    # Either form works - with or without the trailing /gateway. The context path
    # is normalised by `gateway_base_url` below, because the same gateway is
    # addressed two different ways across the codebase and both are legitimate:
    #
    #   React (VITE_API_BASE_URL)  bare host, and every path constant in
    #                              src/constants/apiUrls.js carries /gateway
    #   this platform              context path in the base, so tool paths match
    #                              the Java @RequestMapping values verbatim
    #
    # UAT is the default so a developer machine never points at production by
    # accident. Both hosts are HTTPS only - port 80 is closed.
    API_GATEWAY_URL: str = "https://digipayapiuat.csccloud.in"
    API_GATEWAY_TIMEOUT: int = 30

    # gateway-service sets `server.servlet.context-path=/gateway`, so every
    # controller is mounted beneath it. Set to "" only if a reverse proxy already
    # strips the prefix before the request reaches the gateway.
    API_GATEWAY_CONTEXT_PATH: str = "/gateway"

    # Readiness probe path on the gateway. `/health` is behind Spring Security
    # and answers 401; only the actuator endpoint is publicly readable.
    API_GATEWAY_HEALTH_PATH: str = "/actuator/health"

    # ------------------------------------------------------------------
    # How the caller's token is presented to the gateway.
    #
    # The DigiPay gateway authenticates from the `access_token` COOKIE, not from
    # an Authorization header, and it keeps server-side session state. The two
    # rejections are distinguishable and prove it:
    #
    #   Authorization: Bearer <token>  -> "Full authentication is required to
    #                                     access this resource"   (not recognised)
    #   Cookie: access_token=<token>   -> "Session expired"       (recognised, but
    #                                     the server session had lapsed)
    #
    # Both are sent by default: the cookie is what the gateway actually reads, and
    # the header costs nothing and keeps any Bearer-accepting deployment working.
    # ------------------------------------------------------------------
    GATEWAY_FORWARD_TOKEN_AS_COOKIE: bool = True
    GATEWAY_TOKEN_COOKIE_NAME: str = "access_token"
    LEDGER_API_URL: str = "http://127.0.0.1:8000/api/v1"
    INTERNAL_BYPASS_SECRET: str = "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
    
    # Whether a backend actually serves the SERVICE_ENDPOINTS paths below.
    #
    # The pre-existing tools (getWalletBalance, getLimits, getPassbook, ...) call
    # /wallet, /merchant, /transaction, /ledger, /passbook, /aeps, /notification
    # and /ticket on API_GATEWAY_URL. The DigiPay Spring gateway does NOT serve
    # those prefixes - it serves /v2/* and /v1/upi/* - so every such call comes
    # back 401 and the assistant escalates to human support instead of answering.
    #
    # While this is false, those tools stay registered (nothing is deleted) but
    # are marked UNREACHABLE and hidden from the model's tool catalogue, so the
    # planner picks a gateway tool that works instead. Set it true if you point
    # API_GATEWAY_URL at a backend that really does serve these prefixes.
    LEGACY_MICROSERVICE_ENDPOINTS_ENABLED: bool = False

    SERVICE_ENDPOINTS: Dict[str, str] = {
        "wallet": "/wallet",
        "merchant": "/merchant",
        "transaction": "/transaction",
        "ticket": "/ticket",
        "ledger": "/ledger",
        "passbook": "/passbook",
        "legacy_passbook": "/passbook/legacy",
        "modern_passbook": "/passbook/modern",
        "aeps": "/aeps",
        "notification": "/notification"
    }

    # ------------------------------------------------------------------
    # DigiPay Spring Boot Gateway (gateway-service) controller prefixes.
    #
    # These map 1:1 to the @RequestMapping values declared on
    # com.digipay.gateway.controllers.*. They are kept SEPARATE from
    # SERVICE_ENDPOINTS above so the pre-existing (legacy) DigiPay tool
    # integrations keep resolving exactly as before.
    # ------------------------------------------------------------------
    V2_SERVICE_ENDPOINTS: Dict[str, str] = {
        "admin": "/v2/admin",
        "aeps": "/v2/aeps",
        "aua": "/v2/aua",
        "device": "/v2/device",
        "dsptopup": "/v2/dsptopup",
        "external_client": "/v2/api/client",
        "ledger": "/v2/ledger",
        "notification": "/v2/notification",
        "operator": "/v2/operator",
        "payout": "/v2/payout",
        "services": "/v2/services",
        "txn": "/v2/txn",
        "user": "/v2/user",
        "analytics": "/api/v2",
        "upi": "/v1/upi",
    }

    # ------------------------------------------------------------------
    # Client-side RSA keypair for encrypted gateway responses.
    #
    # GET /v2/ledger/balance requires an X-Frontend-Key header. That header is
    # NOT a shared secret: it is this platform's OWN RSA public key, which the
    # gateway uses to encrypt the balance back to us (see gateway/v2/crypto.py).
    # There is therefore no key to copy from the gateway configuration — we hold
    # our own. The key is generated on first use if the path does not exist.
    # ------------------------------------------------------------------
    GATEWAY_CLIENT_KEY_PATH: str = "data/keys/gateway_client_rsa.pem"
    GATEWAY_CLIENT_KEY_SIZE: int = 2048

    # Verify the backend's SHA256withRSA signature on encrypted responses. The
    # verifying key is fetched from GET /v2/user/publickey at runtime.
    GATEWAY_VERIFY_RESPONSE_SIGNATURE: bool = True

    # ------------------------------------------------------------------
    # Legacy DigiPay API service (app/main.py) — runs as its OWN service.
    #
    # The AI platform calls it over HTTP exactly as any other client would, so
    # its URLs stay unchanged and no frontend has to be touched. Authentication
    # uses the internal-client bypass the legacy AuthMiddleware already supports
    # (X-Client-Id + X-Bypass-Secret).
    # ------------------------------------------------------------------
    LEGACY_API_URL: str = "http://127.0.0.1:8000"
    LEGACY_API_PREFIX: str = "/api/v1"
    # Kept short: the legacy API may live on an internal subnet that is not always
    # reachable, and a 30s timeout made every chat turn hang for half a minute
    # before reporting the failure.
    LEGACY_API_TIMEOUT: int = 10
    LEGACY_INTERNAL_CLIENT_ID: str = "AI_PLATFORM"

    # Browser-facing address of the legacy service, used only in the merged
    # OpenAPI schema. It differs from LEGACY_API_URL whenever the two services
    # talk over a private network: in Docker the server-to-server URL is
    # http://legacy-api:8000, which a browser on the host cannot resolve, so
    # Swagger's "Try it out" would fail. Falls back to LEGACY_API_URL when unset.
    LEGACY_API_PUBLIC_URL: str = ""

    # Merge the legacy service's OpenAPI into this service's /docs so both APIs
    # are documented on one page while still being served by two processes.
    AGGREGATE_LEGACY_OPENAPI: bool = True


class RedisSettings(BaseSettings):
    """
    Redis cache details.
    """
    REDIS_URL: str = "redis://127.0.0.1:6379/2"
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2
    REDIS_PASSWORD: str = ""


class CorsSettings(BaseSettings):
    """
    Browser origins permitted to call this service.

    Comma-separated, or "*" for any origin. The React app calls this service
    cross-origin (dev server on :5173 -> API on :8001), so its origin must be
    listed or the browser blocks every request.
    """
    CORS_ALLOW_ORIGINS: str = "*"

    @property
    def cors_allow_origins(self) -> list:
        raw = (self.CORS_ALLOW_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


class MongoSettings(BaseSettings):
    """
    MongoDB used as the RAG (Retrieval Augmented Generation) knowledge store.

    Works against a plain MongoDB deployment (cosine similarity computed
    in-process) and against MongoDB Atlas Vector Search ($vectorSearch) when
    MONGO_VECTOR_SEARCH_ENABLED is turned on.
    """
    MONGO_URI: str = "mongodb://127.0.0.1:27017"
    MONGO_DB: str = "digipay_ai"
    MONGO_RAG_DOCS_COLLECTION: str = "rag_documents"
    MONGO_RAG_CHUNKS_COLLECTION: str = "rag_chunks"
    MONGO_VECTOR_INDEX: str = "rag_chunk_vector_index"
    MONGO_VECTOR_SEARCH_ENABLED: bool = False
    MONGO_CONNECT_TIMEOUT_MS: int = 3000
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = 3000

    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 4
    RAG_CANDIDATE_POOL: int = 60
    RAG_MIN_SCORE: float = 0.05
    RAG_EMBEDDING_PROVIDER: str = "auto"  # auto | openai | hashing
    RAG_EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAG_EMBEDDING_DIM: int = 512
    RAG_AUTO_SEED: bool = True


class LLMSettings(BaseSettings):
    """
    Decoupled Model Providers.
    """
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.5"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-pro"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.3"


class TracingSettings(BaseSettings):
    """
    Zipkin / B3 tracing settings compatible with Spring Boot Sleuth/Micrometer.
    """
    ENABLE_TRACING: bool = True
    ZIPKIN_ENDPOINT: str = "http://localhost:9411/api/v2/spans"
    TRACE_PROPAGATION: str = "b3"
    SERVICE_NAME: str = "ai-platform"
    TRACE_SAMPLING_RATE: float = 1.0


class MonitoringSettings(BaseSettings):
    """
    Telemetry scrapers configurations.
    """
    ENABLE_TRACING: bool = True
    ENABLE_METRICS: bool = True
    ENABLE_REQUEST_LOGGING: bool = True
    ZIPKIN_BASE_URL: str = "http://localhost:9411"
    ZIPKIN_URL: str = "http://127.0.0.1:9411/api/v2/spans"
    LOG_LEVEL: str = "INFO"


class ChatSettings(BaseSettings):
    """
    Session context threshold properties.
    """
    CHAT_SESSION_TTL: int = 86400
    CONTEXT_WINDOW: int = 20
    MAX_HISTORY: int = 50
    MAX_CHAT_HISTORY: int = 20
    MAX_MESSAGE_LENGTH: int = 5000
    RATE_LIMIT_PER_MINUTE: int = 60


class SecuritySettings(BaseSettings):
    """
    Access parameters.
    """
    JWT_SECRET: str = "hVp48q32qel5J1bJutBWIVKsO4f1FbgA3SwS1lXsoi8="
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: Optional[str] = None
    JWT_AUDIENCE: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cookies to read the caller's token from, in order, when there is no
    # Authorization header. DigiPay stores the browser session in `access_token`.
    JWT_COOKIE_NAMES: str = "access_token,token"

    # ------------------------------------------------------------------
    # DigiPay role name -> this platform's RBAC role.
    #
    # DigiPay tokens carry bare names ("VLE", "ADMIN"); every tool's allow-list
    # is written against ROLE_MERCHANT / ROLE_SUPPORT / ROLE_ADMIN, so without a
    # translation every call is denied.
    #
    # NOTE ON "ADMIN": it is mapped to ROLE_MERCHANT, NOT ROLE_ADMIN. In a
    # DigiPay token that also carries `ownerId` and `operatorIds`, "ADMIN"
    # denotes the owner of a CSC relative to its operators - not a platform
    # administrator. Granting ROLE_ADMIN would hand every CSC owner the
    # platform-wide admin reports (the full user directory, block history,
    # settlement listings) and exempt them from tenant isolation.
    #
    # If your "ADMIN" really does mean a DigiPay platform administrator, change
    # it here:  JWT_ROLE_MAP=VLE=ROLE_MERCHANT,ADMIN=ROLE_ADMIN,...
    # ------------------------------------------------------------------
    JWT_ROLE_MAP: str = (
        "VLE=ROLE_MERCHANT,"
        "ADMIN=ROLE_MERCHANT,"
        "OPERATOR=ROLE_USER,"
        "SUPPORT=ROLE_SUPPORT,"
        "MERCHANT=ROLE_MERCHANT"
    )

    # Applied when a token carries no roles at all.
    JWT_DEFAULT_ROLE: str = "ROLE_MERCHANT"

    @property
    def jwt_cookie_names(self) -> list:
        return [name.strip() for name in (self.JWT_COOKIE_NAMES or "").split(",") if name.strip()]

    @property
    def jwt_role_map(self) -> dict:
        mapping = {}
        for entry in (self.JWT_ROLE_MAP or "").split(","):
            if "=" not in entry:
                continue
            source, target = entry.split("=", 1)
            source, target = source.strip().upper(), target.strip().upper()
            if source and target:
                mapping[source] = target
        return mapping


class Settings(
    AppSettings,
    GatewaySettings,
    CorsSettings,
    RedisSettings,
    MongoSettings,
    LLMSettings,
    TracingSettings,
    MonitoringSettings,
    ChatSettings,
    SecuritySettings
):
    """
    Global Application Settings merging all modular config classes
    using multiple inheritance to maintain flat namespace readability.
    """
    # Later files take precedence, matching app/config.py so both services
    # resolve configuration the same way: .env.prod < .env < .env.local.
    # Real environment variables still override everything, which is how the
    # container passes its settings.
    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(BASE_DIR, ".env.prod"),
            os.path.join(BASE_DIR, ".env"),
            os.path.join(BASE_DIR, ".env.local"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


    @property
    def gateway_base_url(self) -> str:
        """
        Gateway base URL with the context path present exactly once.

        Accepts either spelling of API_GATEWAY_URL so the value the team shares
        (`https://digipayapiuat.csccloud.in`, matching the React app's
        VITE_API_BASE_URL) can be pasted in directly. Both failure modes are
        silent 404s from Tomcat that return HTML rather than a JSON error, so
        they are easy to misread as "the endpoint does not exist":

            missing  /v2/user/publickey                  -> 404
            doubled  /gateway/gateway/v2/user/publickey  -> 404
        """
        base = (self.API_GATEWAY_URL or "").rstrip("/")
        context = (self.API_GATEWAY_CONTEXT_PATH or "").strip("/")
        if not context:
            return base
        if base.endswith(f"/{context}"):
            return base
        return f"{base}/{context}"

    @property
    def legacy_api_public_url(self) -> str:
        """Address to advertise for the legacy service in documentation."""
        return self.LEGACY_API_PUBLIC_URL or self.LEGACY_API_URL


@lru_cache
def get_settings() -> Settings:
    """
    Creates a singleton Settings object loaded once via lru_cache.
    """
    return Settings()


settings = get_settings()
