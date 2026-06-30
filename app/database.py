import logging
from contextvars import ContextVar
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger("digipay.database")

# Multi-tenant context variable
tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

def get_tenant_id() -> Optional[str]:
    return tenant_context.get()

def set_tenant_id(tenant_id: Optional[str]) -> None:
    tenant_context.set(tenant_id)

import urllib.parse

# Database URL formulation
if settings.ENV == "TEST":
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
else:
    safe_password = urllib.parse.quote_plus(settings.DB_PASSWORD)
    DATABASE_URL = (
        f"mysql+aiomysql://{settings.DB_USER}:{safe_password}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

logger.info(f"Configuring database engine for env {settings.ENV}")

# Set up Async Engine
try:
    if settings.ENV == "TEST" or "sqlite" in DATABASE_URL:
        # SQLite engines need specific parameters for concurrent threading
        engine = create_async_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    else:
        # Production/Local MySQL with connection pooling settings
        engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600
        )
except Exception as e:
    logger.error(f"Failed to create MySQL engine: {e}. Falling back to local SQLite.")
    DATABASE_URL = "sqlite+aiosqlite:///./digipay.db"
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

# Async Session Maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# SQLAlchemy Declarative Base
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for DB Sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
