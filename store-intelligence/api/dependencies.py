"""
FastAPI Dependencies

Dependency injection functions for FastAPI routes.
Handles database sessions, authentication, and shared resources.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from storage import get_db_session


async def get_current_session() -> AsyncSession:
    """
    Get current database session.
    
    This dependency injects an AsyncSession into route handlers.
    The session is automatically committed on success and rolled back on error.
    
    Returns:
        AsyncSession: Database session for the request
        
    Raises:
        HTTPException: If session creation fails
        
    Example:
        ```python
        @app.get("/items/")
        async def list_items(session: AsyncSession = Depends(get_current_session)):
            # Use session to query database
            pass
        ```
    """
    async for session in get_db_session():
        yield session


# Annotated aliases for cleaner code
DatabaseSession = Annotated[AsyncSession, Depends(get_current_session)]
"""Type alias for database session dependency."""


async def validate_store_exists(store_id: str, session: DatabaseSession) -> str:
    """
    Validate that a store exists.
    
    Args:
        store_id: Store ID to validate
        session: Database session
        
    Returns:
        store_id: If validation passes
        
    Raises:
        HTTPException: If store not found
    """
    from storage import StoreRepository
    
    repo = StoreRepository(session)
    store = await repo.get_by_store_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store '{store_id}' not found"
        )
    
    return store_id
