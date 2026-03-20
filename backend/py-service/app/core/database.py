"""Database Configuration and Session Management"""

import ssl
from pathlib import Path
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base

from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database base class for models
Base = declarative_base()

# Global engine and session factory
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _get_ssl_context() -> Optional[ssl.SSLContext]:
    """Create SSL context with CA cert for PostgreSQL connection."""
    ca_path = settings.DATABASE_CA_CERT
    if not ca_path:
        return None
    # Resolve path: try relative to project root, then absolute
    # Project root: backend/py-service/app/core/database.py -> 5 levels up
    for base in [Path(__file__).resolve().parent.parent.parent.parent.parent, Path.cwd()]:
        candidate = base / ca_path
        if candidate.exists():
            ca_path = str(candidate)
            break
    else:
        if not Path(ca_path).exists():
            logger.warning(f"CA cert not found: {ca_path}, SSL may fail")
    try:
        ssl_ctx = ssl.create_default_context(cafile=ca_path)
        ssl_ctx.check_hostname = True
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        return ssl_ctx
    except Exception as e:
        logger.warning(f"Failed to create SSL context: {e}")
        return None


async def init_db() -> None:
    """Initialize database connection. DATABASE_URL must be set in .env."""
    global engine, AsyncSessionLocal
    
    if not settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL not set - skipping database init. "
            "Ensure .env exists in backend/py-service/ with DATABASE_URL."
        )
        return
    
    if engine is None:
        connect_args = {}
        if "sslmode=require" in settings.DATABASE_URL:
            ssl_ctx = _get_ssl_context()
            if ssl_ctx:
                connect_args["ssl"] = ssl_ctx
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DATABASE_ECHO,
            future=True,
            connect_args=connect_args,
        )
        
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Create tables (users, drive_files, emails)
        from app.models import User, DriveFile, StoredEmail
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database connection initialized")


async def close_db() -> None:
    """Close database connection"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

