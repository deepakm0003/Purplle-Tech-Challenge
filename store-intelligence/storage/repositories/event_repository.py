"""
Event Repository

Handles all database operations for Event entities.

Provides both ORM-level operations and integration with
Pydantic api.schemas.Event models.
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import selectinload

from storage.models import Event as EventModel, EventType as EventTypeEnum, Store, Camera, Zone
from storage.repositories.base_repository import BaseRepository
from api.schemas import Event, EventType, EventMetadata

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class EventRepository(BaseRepository[EventModel]):
    """Repository for Event entity with Pydantic schema support."""

    def __init__(self, session: AsyncSession):
        """Initialize event repository."""
        super().__init__(session, EventModel)

    # ========================================================================
    # ORM-level queries (using storage.models.Event)
    # ========================================================================

    async def get_by_event_id(self, event_id: str) -> Optional[EventModel]:
        """Get event by event_id."""
        query = select(EventModel).where(EventModel.event_id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_track_id(
        self,
        track_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventModel]:
        """Get all events for a track."""
        query = (
            select(EventModel)
            .where(EventModel.track_id == track_id)
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_store_date_range(
        self,
        store_id: UUID,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
        offset: int = 0
    ) -> List[EventModel]:
        """Get events for store within time range."""
        query = (
            select(EventModel)
            .where(
                and_(
                    EventModel.store_id == store_id,
                    EventModel.timestamp >= start_time,
                    EventModel.timestamp <= end_time
                )
            )
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest_event(self) -> Optional[EventModel]:
        """Return the most recent event, if any."""
        query = select(EventModel).order_by(desc(EventModel.timestamp)).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pydantic_events_for_store(
        self,
        store_id: str,
        limit: int = 10000,
    ) -> List[Event]:
        """Load events for a store and convert to API Pydantic models."""
        query = (
            select(EventModel)
            .join(Store, EventModel.store_id == Store.id)
            .where(Store.store_id == store_id)
            .options(
                selectinload(EventModel.store),
                selectinload(EventModel.camera),
                selectinload(EventModel.zone),
            )
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._model_to_pydantic_event(model) for model in models]

    def _model_to_pydantic_event(self, model: EventModel) -> Event:
        """Convert ORM event to Pydantic Event schema."""
        metadata_raw = model.event_metadata or {}
        if not isinstance(metadata_raw, dict):
            metadata_raw = {}

        return Event(
            event_id=model.event_id,
            store_id=model.store.store_id,
            camera_id=model.camera.camera_id,
            visitor_id=str(model.visitor_id) if model.visitor_id else str(model.track_id),
            event_type=EventType(model.event_type.value),
            timestamp=model.timestamp,
            zone_id=model.zone.zone_id if model.zone else None,
            dwell_ms=model.dwell_ms or 0,
            is_staff=model.is_staff,
            confidence=model.confidence if model.confidence is not None else 0.0,
            metadata=EventMetadata(**metadata_raw),
        )

    async def get_by_event_type(
        self,
        event_type: EventTypeEnum,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventModel]:
        """Get events by type."""
        query = (
            select(EventModel)
            .where(EventModel.event_type == event_type)
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_zone_id(
        self,
        zone_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventModel]:
        """Get events for a zone."""
        query = (
            select(EventModel)
            .where(EventModel.zone_id == zone_id)
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Pydantic schema support (for Phase 2 pipeline)
    # ========================================================================

    async def save_pydantic_event(
        self,
        event: Event,
        store_id: UUID,
        camera_id: UUID,
        track_id: UUID = None,
        zone_id: UUID = None,
        visitor_id: UUID = None
    ) -> bool:
        """
        Save Pydantic Event schema to database (idempotent).

        Args:
            event: Pydantic Event schema
            store_id: Store UUID
            camera_id: Camera UUID
            track_id: Optional track UUID
            zone_id: Optional zone UUID
            visitor_id: Optional visitor UUID

        Returns:
            True if saved, False if already exists
        """
        try:
            # Check if event already exists
            existing = await self.get_by_event_id(event.event_id)
            if existing:
                logger.debug(f"Event {event.event_id} already exists")
                return False

            # Convert to ORM model
            model = EventModel(
                event_id=event.event_id,
                event_type=EventTypeEnum[event.event_type.value],
                store_id=store_id,
                camera_id=camera_id,
                track_id=track_id or uuid4(),
                zone_id=zone_id,
                visitor_id=visitor_id,
                timestamp=event.timestamp,
                dwell_ms=event.dwell_ms,
                is_staff=event.is_staff,
                confidence=event.confidence,
                event_metadata=event.metadata.model_dump()
            )

            self.session.add(model)
            await self.session.flush()
            logger.debug(f"Saved Pydantic event: {event.event_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving Pydantic event: {e}")
            await self.session.rollback()
            return False

    async def save_pydantic_batch(
        self,
        events: List[Event],
        store_id: UUID,
        camera_id: UUID,
        track_id: UUID = None,
        zone_id: UUID = None,
        visitor_id: UUID = None
    ) -> int:
        """
        Save batch of Pydantic events.

        Args:
            events: List of Pydantic events
            store_id: Store UUID
            camera_id: Camera UUID
            track_id: Optional track UUID
            zone_id: Optional zone UUID
            visitor_id: Optional visitor UUID

        Returns:
            Number of events saved
        """
        if not events:
            return 0

        try:
            saved = 0
            for event in events:
                if await self.save_pydantic_event(
                    event,
                    store_id,
                    camera_id,
                    track_id,
                    zone_id,
                    visitor_id
                ):
                    saved += 1

            await self.session.commit()
            logger.info(f"Saved Pydantic batch: {saved}/{len(events)}")
            return saved

        except Exception as e:
            logger.error(f"Error in batch save: {e}")
            await self.session.rollback()
            return 0

    async def get_events_by_store_string(
        self,
        store_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventModel]:
        """
        Get events by store identifier string.

        Args:
            store_id: Store identifier (string)
            limit: Query limit
            offset: Query offset

        Returns:
            List of events
        """
        # This would require a JOIN with Store table
        from storage.models import Store
        query = (
            select(EventModel)
            .join(Store)
            .where(Store.store_id == store_id)
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_events_by_visitor_string(
        self,
        visitor_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventModel]:
        """
        Get events by visitor identifier string.

        Args:
            visitor_id: Visitor identifier (string)
            limit: Query limit
            offset: Query offset

        Returns:
            List of events
        """
        # Assuming metadata contains visitor reference
        query = (
            select(EventModel)
            .where(EventModel.metadata['visitor_id'].astext == visitor_id)
            .order_by(desc(EventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_store_uuid(self, store_id: UUID) -> int:
        """Count events for store UUID."""
        try:
            query = select(func.count(EventModel.id)).where(
                EventModel.store_id == store_id
            )
            result = await self.session.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0

    async def deduplicate_by_event_id(self, event_id: str) -> bool:
        """
        Check if event_id already exists (for deduplication).

        Args:
            event_id: Event ID

        Returns:
            True if exists, False otherwise
        """
        try:
            query = select(EventModel).where(EventModel.event_id == event_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking deduplication: {e}")
            return False

    async def delete_event_by_id(self, event_id: str) -> bool:
        """
        Delete event by event_id.

        Args:
            event_id: Event ID

        Returns:
            True if deleted, False if not found
        """
        try:
            model = await self.get_by_event_id(event_id)
            if not model:
                return False

            await self.session.delete(model)
            await self.session.commit()
            logger.debug(f"Deleted event: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            await self.session.rollback()
            return False

