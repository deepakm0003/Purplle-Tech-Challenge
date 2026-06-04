"""
Visitor Repository

Handles all database operations for Visitor entities.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from storage.models import Visitor
from storage.repositories.base_repository import BaseRepository


class VisitorRepository(BaseRepository[Visitor]):
    """Repository for Visitor entity."""

    def __init__(self, session: AsyncSession):
        """Initialize visitor repository."""
        super().__init__(session, Visitor)

    async def get_by_visitor_id(
        self,
        store_id: UUID,
        visitor_id: str
    ) -> Optional[Visitor]:
        """Get visitor by visitor_id and store."""
        query = select(Visitor).where(
            (Visitor.store_id == store_id) & (Visitor.visitor_id == visitor_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_store_visitors(
        self,
        store_id: UUID,
        limit: int = 1000,
        offset: int = 0
    ) -> list[Visitor]:
        """Get all visitors for a store."""
        query = (
            select(Visitor)
            .where(Visitor.store_id == store_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
