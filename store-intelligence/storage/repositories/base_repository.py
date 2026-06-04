"""
Base Repository Class

Abstract base class for all repositories, providing common CRUD operations
and query patterns using SQLAlchemy 2.0 async patterns.
"""

from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from storage.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic repository for CRUD operations.
    
    Provides a common interface for all entity repositories,
    reducing code duplication and ensuring consistency.
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        Initialize repository with session and model.
        
        Args:
            session: AsyncSession for database operations
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def create(self, **kwargs) -> T:
        """
        Create a new entity.
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            Created entity instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Get entity by primary key.
        
        Args:
            entity_id: UUID primary key
            
        Returns:
            Entity instance or None
        """
        return await self.session.get(self.model, entity_id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Max results to return
            offset: Number of results to skip
            
        Returns:
            List of entity instances
        """
        query = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """
        Update entity attributes.
        
        Args:
            entity_id: UUID primary key
            **kwargs: Attributes to update
            
        Returns:
            Updated entity instance or None
        """
        instance = await self.get_by_id(entity_id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            await self.session.flush()
        return instance

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete entity by primary key.
        
        Args:
            entity_id: UUID primary key
            
        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(entity_id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False

    async def count(self) -> int:
        """
        Count total entities.
        
        Returns:
            Total count
        """
        query = select(func.count(self.model.id))
        result = await self.session.execute(query)
        return result.scalar() or 0
