import json
from typing import Dict, List, Set, Any, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "LOCAL"
    
    # Database Settings
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "digipay"
    
    # JWT Settings
    JWT_SECRET: str = "hVp48q32qel5J1bJutBWIVKsO4f1FbgA3SwS1lXsoi8="
    JWT_EXPIRY_SECONDS: int = 21600
    
    # Redis Settings
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    
    # Rate Limit Settings
    RATE_LIMIT: int = 100
    RATE_WINDOW: int = 60
    
    # API Deprecation Governance
    DEPRECATED_API_VERSION: str = "v1"
    API_SUNSET_DATE: str = "2026-12-31"
    DEPRECATION_BLOCK_AFTER_SUNSET: bool = True
    DEPRECATION_WARN_BEFORE_SUNSET: bool = True
    
    # Deprecation Rules (Parsed from JSON)
    API_DEPRECATION_RULES_JSON: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    DEPRECATION_CANARY_PERCENT: float = 0.0  # e.g., 1% -> 1.0 (or 0.01 depending on logic, let's support both or treat as percentage like 1%)
    API_CHANGELOG_JSON: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    # Internal Auth Bypass
    ENABLE_INTERNAL_AUTH_BYPASS: bool = True
    INTERNAL_CLIENTS: str = "WALLET_SERVICE,PASSBOOK_SERVICE,LOG_SERVICE"
    INTERNAL_BYPASS_SECRET: str = "NPCl_INT3RNAL_Bypass_Secr3t_2026!" # Shared secret to protect bypass from spoofing

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env.prod"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("API_DEPRECATION_RULES_JSON", mode="before")
    @classmethod
    def parse_deprecation_rules(cls, v: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    @field_validator("API_CHANGELOG_JSON", mode="before")
    @classmethod
    def parse_changelog(cls, v: Any) -> Dict[str, List[Dict[str, Any]]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    @property
    def internal_clients_set(self) -> Set[str]:
        return {client.strip() for client in self.INTERNAL_CLIENTS.split(",") if client.strip()}

# Global settings instance
settings = Settings()
