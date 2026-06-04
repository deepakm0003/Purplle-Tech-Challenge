"""
Track Repository

Handles all database operations for Track entities.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc

from storage.models import Track
from storage.repositories.base_repository import BaseRepository


class TrackRepository(BaseRepository[Track]):
    """Repository for Track entity."""

    def __init__(self, session: AsyncSession):
        """Initialize track repository."""
        super().__init__(session, Track)

    async def get_by_track_id(self, track_id: int) -> Optional[Track]:
        """Get track by numeric ID."""
        query = select(Track).where(Track.track_id == track_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_visitor_id(
        self,
        visitor_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Track]:
        """Get all tracks for a visitor."""
        query = (
            select(Track)
            .where(Track.visitor_id == visitor_id)
            .order_by(desc(Track.entry_time))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_store_active_tracks(self, store_id: UUID) -> List[Track]:
        """Get currently active tracks in a store (no exit_time)."""
        query = (
            select(Track)
            .where(
                and_(
                    Track.store_id == store_id,
                    Track.exit_time == None
                )
            )
            .order_by(Track.entry_time)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_store_date_range(
        self,
        store_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> List[Track]:
        """Get tracks for store within time range."""
        query = (
            select(Track)
            .where(
                and_(
                    Track.store_id == store_id,
                    Track.entry_time >= start_time,
                    Track.entry_time <= end_time
                )
            )
            .order_by(desc(Track.entry_time))
        )
        result = await self.session.execute(query)
        return result.scalars().all()
