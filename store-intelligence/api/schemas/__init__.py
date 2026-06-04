"""API Pydantic Schemas - Event Models and API Responses"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import uuid


# ============================================================================
# Base Response Models
# ============================================================================
class BaseResponse(BaseModel):
    """Base response model with metadata."""
    success: bool = Field(default=True, description="Whether request was successful")
    message: Optional[str] = Field(default=None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")
    trace_id: Optional[str] = Field(default=None, description="Request trace ID")

    class Config:
        from_attributes = True


# ============================================================================
# Event Type Enums
# ============================================================================
class EventType(str, Enum):
    """Event type enumeration per Purplle schema."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


# ============================================================================
# Event Schema - Per Purplle Specification
# ============================================================================
class EventMetadata(BaseModel):
    """Event metadata container."""
    queue_depth: Optional[int] = Field(default=None, description="Billing queue depth")
    sku_zone: Optional[str] = Field(default=None, description="Product zone label")
    session_seq: Optional[int] = Field(default=None, description="Session event sequence number")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        from_attributes = True


class Event(BaseModel):
    """
    Retail Event - Purplle Schema.
    
    Represents a single behavioral event from CCTV pipeline.
    UUID, timestamp, and confidence are required.
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="UUID v4 - globally unique")
    store_id: str = Field(description="Store identifier from store_layout.json")
    camera_id: str = Field(description="Camera identifier (e.g., CAM_ENTRY_01)")
    visitor_id: str = Field(description="Unique visitor/session identifier")
    event_type: EventType = Field(description="Event type from catalogue")
    timestamp: datetime = Field(description="ISO-8601 UTC timestamp")
    zone_id: Optional[str] = Field(default=None, description="Zone ID from store_layout.json, null for ENTRY/EXIT")
    dwell_ms: int = Field(default=0, description="Duration in milliseconds; 0 for instantaneous events")
    is_staff: bool = Field(default=False, description="Whether visitor is staff member")
    confidence: float = Field(description="Detection confidence 0-1")
    metadata: EventMetadata = Field(default_factory=EventMetadata, description="Event metadata")

    @root_validator(pre=True)
    @classmethod
    def pre_validate(cls, values: dict) -> dict:
        """Root validator to handle both original event schema and new sample_events schema."""
        # 1. Map event_id
        if "event_id" not in values and "id" in values:
            values["event_id"] = str(values["id"])
        elif "event_id" not in values and "queue_event_id" in values:
            values["event_id"] = str(values["queue_event_id"])
        elif "event_id" not in values:
            values["event_id"] = str(uuid.uuid4())

        # 2. Map store_id
        if "store_id" not in values:
            if "store_code" in values:
                val = str(values["store_code"])
                if val.startswith("store_"):
                    values["store_id"] = "ST" + val.split("_")[1]
                else:
                    values["store_id"] = val
            else:
                values["store_id"] = "ST1008"
        else:
            val = str(values["store_id"])
            if val.startswith("store_"):
                values["store_id"] = "ST" + val.split("_")[1]

        # 3. Map visitor_id
        if "visitor_id" not in values:
            if "id_token" in values:
                values["visitor_id"] = str(values["id_token"])
            elif "track_id" in values:
                values["visitor_id"] = f"VIS_{values['track_id']}"
            else:
                values["visitor_id"] = "VIS_unknown"

        # 4. Map event_type (string / sample schema only — keep EventType instances as-is)
        if "event_type" in values and not isinstance(values["event_type"], EventType):
            et = str(values["event_type"]).upper()
            if "." in et:
                et = et.rsplit(".", 1)[-1]
            if et == "ENTRY":
                values["event_type"] = EventType.ENTRY
            elif et == "EXIT":
                values["event_type"] = EventType.EXIT
            elif et in ("ZONE_ENTERED", "ZONE_ENTER"):
                values["event_type"] = EventType.ZONE_ENTER
            elif et in ("ZONE_EXITED", "ZONE_EXIT"):
                values["event_type"] = EventType.ZONE_EXIT
            elif et == "ZONE_DWELL":
                values["event_type"] = EventType.ZONE_DWELL
            elif et in ("QUEUE_COMPLETED", "BILLING_QUEUE_JOIN"):
                # If it has abandoned=true, it is an abandon
                if values.get("abandoned") is True:
                    values["event_type"] = EventType.BILLING_QUEUE_ABANDON
                else:
                    values["event_type"] = EventType.BILLING_QUEUE_JOIN
            elif et in ("QUEUE_ABANDONED", "BILLING_QUEUE_ABANDON"):
                values["event_type"] = EventType.BILLING_QUEUE_ABANDON
            elif et == "REENTRY":
                values["event_type"] = EventType.REENTRY
            else:
                values["event_type"] = EventType.ZONE_DWELL

        # 5. Map timestamp
        if "timestamp" not in values:
            if "event_timestamp" in values:
                values["timestamp"] = values["event_timestamp"]
            elif "event_time" in values:
                values["timestamp"] = values["event_time"]
            elif "queue_join_ts" in values:
                values["timestamp"] = values["queue_join_ts"]
            else:
                values["timestamp"] = datetime.utcnow().isoformat()

        # 6. Map dwell_ms
        if "dwell_ms" not in values:
            if "wait_seconds" in values and values["wait_seconds"] is not None:
                values["dwell_ms"] = int(values["wait_seconds"] * 1000)
            elif "queue_exit_ts" in values and "queue_join_ts" in values:
                try:
                    t1 = datetime.fromisoformat(values["queue_join_ts"].replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(values["queue_exit_ts"].replace("Z", "+00:00"))
                    values["dwell_ms"] = int((t2 - t1).total_seconds() * 1000)
                except Exception:
                    values["dwell_ms"] = 0
            else:
                values["dwell_ms"] = 0

        # 7. Map confidence
        if "confidence" not in values:
            values["confidence"] = 1.0

        # 8. Map is_staff
        if "is_staff" not in values:
            values["is_staff"] = False

        return values
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_c8a2f1",
                "event_type": "ZONE_DWELL",
                "timestamp": "2026-03-03T14:22:10Z",
                "zone_id": "SKINCARE",
                "dwell_ms": 8400,
                "is_staff": False,
                "confidence": 0.91,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": "MOISTURISER",
                    "session_seq": 5
                }
            }
        }
    
    @validator('event_id')
    def validate_event_id(cls, v):
        """Ensure event_id is valid UUID."""
        if not v:
            return str(uuid4())
        try:
            UUID(v)
        except ValueError:
            raise ValueError("event_id must be valid UUID v4")
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is in [0, 1]."""
        if not 0 <= v <= 1:
            raise ValueError("confidence must be in [0, 1]")
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is valid datetime."""
        if not isinstance(v, datetime):
            raise ValueError("timestamp must be datetime")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'event_id': self.event_id,
            'store_id': self.store_id,
            'camera_id': self.camera_id,
            'visitor_id': self.visitor_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'zone_id': self.zone_id,
            'dwell_ms': self.dwell_ms,
            'is_staff': self.is_staff,
            'confidence': self.confidence,
            'metadata': self.metadata.dict()
        }


class EventBatch(BaseModel):
    """Batch of events for ingestion."""
    events: List[Event] = Field(description="List of events")
    
    class Config:
        from_attributes = True


class EventResponse(BaseResponse):
    """Response from event ingest endpoint."""
    event_id: str = Field(description="ID of ingested event")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class EventBatchResponse(BaseResponse):
    """Response from batch ingest endpoint."""
    total: int = Field(description="Total events in batch")
    ingested: int = Field(description="Successfully ingested")
    failed: int = Field(description="Failed to ingest")
    failed_ids: List[str] = Field(default_factory=list)


# ============================================================================
# Query/Filter Models
# ============================================================================
class EventQuery(BaseModel):
    """Query parameters for event listing."""
    store_id: Optional[str] = Field(default=None)
    visitor_id: Optional[str] = Field(default=None)
    event_type: Optional[EventType] = Field(default=None)
    zone_id: Optional[str] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
    class Config:
        from_attributes = True


__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "EventType",
    "EventMetadata",
    "Event",
    "EventBatch",
    "EventResponse",
    "EventBatchResponse",
    "EventQuery",
]
