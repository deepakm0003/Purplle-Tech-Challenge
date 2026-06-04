"""
Analytics Response Schemas.

Pydantic models for analytics API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from api.schemas import BaseResponse


class MetricsResponse(BaseResponse):
    """Store metrics response."""
    
    unique_visitors: int = Field(description="Unique visitor count")
    conversion_rate: float = Field(description="Conversion rate 0-1")
    average_dwell_time: int = Field(description="Average dwell time in seconds")
    average_dwell_by_zone: Dict[str, int] = Field(description="Dwell per zone")
    queue_depth: int = Field(description="Peak queue depth")
    abandonment_rate: float = Field(description="Queue abandonment rate")
    revenue: float = Field(description="Total revenue INR")
    average_basket_size: float = Field(description="Average transaction INR")
    store_footfall: int = Field(description="Total store entries")
    zone_visit_frequency: Dict[str, int] = Field(description="Visits per zone")
    
    class Config:
        from_attributes = True


class FunnelResponse(BaseResponse):
    """Conversion funnel response."""
    
    entry_count: int = Field(description="Store entries")
    zone_count: int = Field(description="Zone visitors")
    billing_count: int = Field(description="Billing queue visitors")
    purchase_count: int = Field(description="Purchases")
    dropoff_percentages: Dict[str, float] = Field(description="Dropoff %")
    efficiency_percentage: float = Field(description="Overall efficiency %")
    
    class Config:
        from_attributes = True


class HeatmapZoneData(BaseModel):
    """Single zone in heatmap."""
    
    zone_id: str
    visit_frequency: int
    avg_dwell_seconds: int
    normalized_heat_score: float
    total_dwell_seconds: int


class HeatmapResponse(BaseResponse):
    """Heatmap response."""
    
    zones: List[HeatmapZoneData] = Field(description="Zone heatmaps")
    data_confidence: str = Field(description="Data confidence (HIGH/LOW)")
    total_sessions: int = Field(description="Total zone sessions")
    zone_count: int = Field(description="Number of zones")
    
    class Config:
        from_attributes = True


class AnomalyData(BaseModel):
    """Single anomaly."""
    
    anomaly_type: str
    severity: str
    description: str
    metric_value: float
    threshold: float
    suggested_action: str
    detected_at: datetime


class AnomaliesResponse(BaseResponse):
    """Anomalies response."""
    
    total_anomalies: int = Field(description="Total anomaly count")
    critical: int = Field(description="Critical count")
    warning: int = Field(description="Warning count")
    info: int = Field(description="Info count")
    anomalies: List[AnomalyData] = Field(description="Detected anomalies")
    
    class Config:
        from_attributes = True


class HealthStatus(BaseModel):
    """Single health check."""
    
    service: str
    status: str  # UP or DOWN
    details: Optional[str] = None


class HealthResponse(BaseResponse):
    """Health check response."""
    
    status: str = Field(description="Overall status (UP/DEGRADED/DOWN)")
    database: HealthStatus = Field(description="Database status")
    redis: HealthStatus = Field(description="Redis status")
    last_event_timestamp: Optional[datetime] = Field(description="Last event time")
    stale_feed_warning: bool = Field(description="Feed is stale (>5 min)")
    checks: List[HealthStatus] = Field(description="All health checks")
    
    class Config:
        from_attributes = True


class EventIngestRequest(BaseModel):
    """Event batch ingest request."""
    
    events: List[Dict[str, Any]] = Field(description="Event data (raw JSON)")
    
    class Config:
        from_attributes = True


class EventIngestResponse(BaseResponse):
    """Event ingest response."""
    
    total: int = Field(description="Total events in batch")
    ingested: int = Field(description="Successfully ingested")
    failed: int = Field(description="Failed to ingest")
    failed_ids: List[str] = Field(default_factory=list, description="Failed event IDs")
    
    class Config:
        from_attributes = True


__all__ = [
    "MetricsResponse",
    "FunnelResponse",
    "HeatmapResponse",
    "HeatmapZoneData",
    "AnomaliesResponse",
    "AnomalyData",
    "HealthResponse",
    "HealthStatus",
    "EventIngestRequest",
    "EventIngestResponse",
]
