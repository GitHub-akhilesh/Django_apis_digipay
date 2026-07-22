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

from functools import lru_cache
from typing import Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    API_GATEWAY_URL: str = "http://localhost:8080"
    API_GATEWAY_TIMEOUT: int = 30
    LEDGER_API_URL: str = "http://127.0.0.1:8000/api/v1"
    INTERNAL_BYPASS_SECRET: str = "NPCI_INT3RNAL_Bypass_Secr3t_2026!"
    
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


class RedisSettings(BaseSettings):
    """
    Redis cache details.
    """
    REDIS_URL: str = "redis://127.0.0.1:6379/2"
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2
    REDIS_PASSWORD: str = ""


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


class Settings(
    AppSettings,
    GatewaySettings,
    RedisSettings,
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
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Creates a singleton Settings object loaded once via lru_cache.
    """
    return Settings()


settings = get_settings()
