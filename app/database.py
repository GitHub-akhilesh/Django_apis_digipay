import logging
import os
import urllib.parse
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

# Database URL formulation
if settings.ENV == "TEST":
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
elif os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
elif settings.DB_HOST and settings.DB_HOST != "127.0.0.1":
    encoded_pass = urllib.parse.quote_plus(settings.DB_PASSWORD or "")
    DATABASE_URL = f"mysql+aiomysql://{settings.DB_USER}:{encoded_pass}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
else:
    DATABASE_URL = "sqlite+aiosqlite:///./digipay.db"

logger.info(f"Configuring database engine for env {settings.ENV} with URL {DATABASE_URL}")

# Set up Async Engine
if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600
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
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            await session.close()
