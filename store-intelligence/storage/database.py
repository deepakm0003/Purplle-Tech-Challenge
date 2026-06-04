"""
Database Connection and Session Management

This module handles:
- SQLAlchemy async engine creation
- Session factory configuration
- Connection pooling and lifecycle
- Database initialization

Uses PostgreSQL with asyncpg for non-blocking operations.
Implements connection pooling with health checks and recycling.
"""

from typing import AsyncGenerator, Optional
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import declarative_base

from configs import get_settings

logger = logging.getLogger(__name__)

# ============================================================================
# ORM Base Class
# ============================================================================
Base = declarative_base()
"""SQLAlchemy declarative base for all ORM models."""

# ============================================================================
# Global Engine and Session Factory
# ============================================================================
_engine = None
_async_session_factory = None


def _create_engine():
    """
    Create and configure the async SQLAlchemy engine.
    
    Configuration:
    - Uses asyncpg driver for PostgreSQL
    - Implements connection pooling with QueuePool
    - Enables connection health checks (pre_ping)
    - Recycles connections after 1 hour to prevent timeout
    - Sets appropriate pool sizes for concurrent requests
    
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
    """
    settings = get_settings()

    # SQLite (dev) and PostgreSQL use different driver connect_args
    connect_args: dict = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {
            "server_settings": {
                "application_name": "store-intelligence",
                "jit": "off",
            },
            "timeout": 10,
        }

    engine_kwargs: dict = {
        "url": settings.database_url,
        "echo": settings.database_echo,
        "echo_pool": settings.database_echo,
        "future": True,
        "connect_args": connect_args,
    }

    if not settings.database_url.startswith("sqlite"):
        engine_kwargs.update(
            poolclass=QueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=settings.database_pool_pre_ping,
            pool_recycle=settings.database_pool_recycle,
        )

    engine = create_async_engine(**engine_kwargs)
    
    logger.info(
        "Database engine created | "
        f"URL: {settings.database_url} | "
        f"Pool size: {settings.database_pool_size} | "
        f"Max overflow: {settings.database_max_overflow}"
    )
    
    return engine


def get_engine():
    """
    Get or create the global async engine.
    
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
    """
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_async_session_factory():
    """
    Get or create the global async session factory.
    
    Returns:
        async_sessionmaker: Factory for creating AsyncSession instances
    """
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects accessible after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Explicit transaction control
        )
    return _async_session_factory


# ============================================================================
# Module-level convenience exports
# ============================================================================
engine = property(lambda self: get_engine())
"""Global async engine instance."""

AsyncSessionLocal = get_async_session_factory
"""Factory function for creating AsyncSession instances."""


# ============================================================================
# Dependency Injection
# ============================================================================
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Creates a new AsyncSession for each request and ensures proper cleanup.
    This generator is designed to be used with FastAPI's Depends() mechanism.
    
    Yields:
        AsyncSession: Database session for the request
        
    Example:
        ```python
        from fastapi import Depends
        from storage import get_db_session
        
        @app.get("/items/")
        async def list_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()
        ```
    """
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# Database Initialization and Teardown
# ============================================================================
async def init_db() -> None:
    """
    Initialize the database schema.
    
    Creates all tables defined in ORM models.
    Safe to call multiple times (existing tables are skipped).
    
    Usage:
        ```python
        import asyncio
        from storage import init_db
        
        asyncio.run(init_db())
        ```
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized")


async def drop_db() -> None:
    """
    Drop all database tables.
    
    CAUTION: This destroys all data. Only use in development/testing.
    
    Usage:
        ```python
        import asyncio
        from storage import drop_db
        
        asyncio.run(drop_db())
        ```
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Database schema dropped - all tables deleted")


async def close_db() -> None:
    """
    Close database connections.
    
    Should be called during application shutdown to cleanly dispose
    of the connection pool.
    
    Usage:
        ```python
        import asyncio
        from storage import close_db
        
        asyncio.run(close_db())
        ```
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database connections closed")
