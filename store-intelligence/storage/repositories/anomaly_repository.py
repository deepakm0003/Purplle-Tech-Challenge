"""
Anomaly Repository

Handles all database operations for Anomaly entities.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc

from storage.models import Anomaly, AnomalySeverity, AnomalyType
from storage.repositories.base_repository import BaseRepository


class AnomalyRepository(BaseRepository[Anomaly]):
    """Repository for Anomaly entity."""

    def __init__(self, session: AsyncSession):
        """Initialize anomaly repository."""
        super().__init__(session, Anomaly)

    async def get_by_anomaly_id(self, anomaly_id: str) -> Optional[Anomaly]:
        """Get anomaly by anomaly_id."""
        query = select(Anomaly).where(Anomaly.anomaly_id == anomaly_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_store_id(
        self,
        store_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Anomaly]:
        """Get anomalies for a store."""
        query = (
            select(Anomaly)
            .where(Anomaly.store_id == store_id)
            .order_by(desc(Anomaly.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_unacknowledged(
        self,
        store_id: UUID,
        limit: int = 50
    ) -> List[Anomaly]:
        """Get unacknowledged anomalies for a store."""
        query = (
            select(Anomaly)
            .where(
                and_(
                    Anomaly.store_id == store_id,
                    Anomaly.is_acknowledged == False
                )
            )
            .order_by(desc(Anomaly.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_severity(
        self,
        severity: AnomalySeverity,
        limit: int = 100
    ) -> List[Anomaly]:
        """Get anomalies by severity."""
        query = (
            select(Anomaly)
            .where(Anomaly.severity == severity)
            .order_by(desc(Anomaly.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_type_and_store(
        self,
        anomaly_type: AnomalyType,
        store_id: UUID,
        limit: int = 50
    ) -> List[Anomaly]:
        """Get anomalies by type for a store."""
        query = (
            select(Anomaly)
            .where(
                and_(
                    Anomaly.anomaly_type == anomaly_type,
                    Anomaly.store_id == store_id
                )
            )
            .order_by(desc(Anomaly.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
