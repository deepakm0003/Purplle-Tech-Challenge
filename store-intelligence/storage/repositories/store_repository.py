"""
Store Repository

Handles all database operations for Store entities.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from storage.models import Store
from storage.repositories.base_repository import BaseRepository


class StoreRepository(BaseRepository[Store]):
    """Repository for Store entity."""

    def __init__(self, session: AsyncSession):
        """Initialize store repository."""
        super().__init__(session, Store)

    async def get_by_store_id(self, store_id: str) -> Optional[Store]:
        """Get store by business identifier."""
        query = select(Store).where(Store.store_id == store_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_stores(self) -> list[Store]:
        """Get all active stores."""
        query = select(Store).where(Store.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()
