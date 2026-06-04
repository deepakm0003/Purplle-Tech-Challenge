"""
SQLAlchemy ORM Models

Defines all database tables using SQLAlchemy 2.0 declarative syntax.

Tables:
- Store: Physical retail locations
- Camera: CCTV cameras within stores
- Zone: Semantic regions in stores (e.g., Skincare aisle)
- Track: Tracked persons during visits (stable identity)
- Visitor: Unique customers
- Event: Behavioral events (zone visits, dwell, etc.)
- Anomaly: Detected anomalies (queue spikes, unusual behavior)

All tables use:
- UUID primary keys for global uniqueness
- Timestamps with UTC timezone
- Constraints and indexes for performance
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from storage.database import Base


# ============================================================================
# Enums
# ============================================================================
class EventType(str, enum.Enum):
    """Types of events that can be detected."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


class AnomalyType(str, enum.Enum):
    """Types of detected anomalies."""
    QUEUE_SPIKE = "QUEUE_SPIKE"
    CONVERSION_DROP = "CONVERSION_DROP"
    DEAD_ZONE = "DEAD_ZONE"
    LONG_DWELL = "LONG_DWELL"
    UNUSUAL_PATH = "UNUSUAL_PATH"
    CROWD_SPIKE = "CROWD_SPIKE"


class AnomalySeverity(str, enum.Enum):
    """Severity levels for anomalies."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ============================================================================
# Store Model
# ============================================================================
class Store(Base):
    """
    Physical retail location.
    
    Attributes:
        id: Unique identifier (UUID)
        store_id: Business identifier (e.g., STORE-BLR-01)
        name: Human-readable store name
        address: Full address
        timezone: IANA timezone (e.g., Asia/Kolkata)
        open_hour: Store opening hour (0-23)
        close_hour: Store closing hour (0-23)
        is_active: Whether store is currently operational
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(512), nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)
    open_hour = Column(Integer, default=9, nullable=False)
    close_hour = Column(Integer, default=21, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    cameras = relationship("Camera", back_populates="store", cascade="all, delete-orphan")
    zones = relationship("Zone", back_populates="store", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="store", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="store", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="store", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Store {self.store_id}>"


# ============================================================================
# Camera Model
# ============================================================================
class Camera(Base):
    """
    CCTV camera within a store.
    
    Attributes:
        id: Unique identifier (UUID)
        camera_id: Business identifier (e.g., CAM-ENTRY-01)
        store_id: Foreign key to Store
        name: Camera name/location
        zone_coverage: Zones covered by this camera
        rtsp_url: RTSP stream URL
        is_active: Whether camera is recording
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    camera_id = Column(String(32), nullable=False, index=True)
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    zone_coverage = Column(ARRAY(String), nullable=True)  # e.g., ['SKINCARE', 'MAKEUP']
    rtsp_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    store = relationship("Store", back_populates="cameras")
    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("store_id", "camera_id", name="uq_camera_store_id"),
    )

    def __repr__(self) -> str:
        return f"<Camera {self.camera_id}>"


# ============================================================================
# Zone Model
# ============================================================================
class Zone(Base):
    """
    Semantic region within a store.
    
    Attributes:
        id: Unique identifier (UUID)
        zone_id: Business identifier (e.g., SKINCARE)
        store_id: Foreign key to Store
        name: Human-readable zone name
        description: Zone description
        polygon: Pixel coordinates defining zone boundary
        color: Hex color for heatmap visualization
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    zone_id = Column(String(32), nullable=False, index=True)
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    polygon = Column(JSON, nullable=False)  # [[x1,y1], [x2,y2], ...]
    color = Column(String(7), default="#FF0000", nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    store = relationship("Store", back_populates="zones")
    events = relationship("Event", back_populates="zone", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("store_id", "zone_id", name="uq_zone_store_id"),
    )

    def __repr__(self) -> str:
        return f"<Zone {self.zone_id}>"


# ============================================================================
# Visitor Model
# ============================================================================
class Visitor(Base):
    """
    Unique customer.
    
    Attributes:
        id: Unique identifier (UUID)
        visitor_id: Re-ID token (stable identifier within visit)
        store_id: Foreign key to Store
        first_seen: Timestamp of first detection
        last_seen: Timestamp of last detection
        total_visits: Cumulative visit count
        created_at: Record creation timestamp
    """
    __tablename__ = "visitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    visitor_id = Column(String(64), nullable=False, index=True)
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    first_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    total_visits = Column(Integer, default=1, nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    tracks = relationship("Track", back_populates="visitor", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint("store_id", "visitor_id", name="uq_visitor_store_id"),
    )

    def __repr__(self) -> str:
        return f"<Visitor {self.visitor_id}>"


# ============================================================================
# Track Model
# ============================================================================
class Track(Base):
    """
    Tracked person during a store visit.
    
    Attributes:
        id: Unique identifier (UUID)
        track_id: Numeric ID from tracker (frame-scoped)
        visitor_id: FK to Visitor (re-ID token across visits)
        store_id: Foreign key to Store
        camera_id: Foreign key to Camera
        entry_time: When person entered store/camera view
        exit_time: When person exited store/camera view
        is_staff: Whether person is identified as staff
        confidence: Average detection confidence
        total_dwell_seconds: Sum of dwell in all zones
        zones_visited: Array of zone IDs visited
        session_seq: Ordinal position in session
        metadata: JSON metadata
        created_at: Record creation timestamp
    """
    __tablename__ = "tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    track_id = Column(Integer, nullable=False)
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id", ondelete="CASCADE"),
        nullable=True,  # May be None before re-ID
        index=True
    )
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    entry_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    exit_time = Column(DateTime(timezone=True), nullable=True)
    is_staff = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, nullable=True)
    total_dwell_seconds = Column(Integer, default=0, nullable=False)
    zones_visited = Column(ARRAY(String), nullable=True)
    session_seq = Column(Integer, nullable=True)
    track_metadata = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    visitor = relationship("Visitor", back_populates="tracks")
    store = relationship("Store", back_populates="tracks")
    camera = relationship("Camera")
    events = relationship("Event", back_populates="track", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_track_store_id_entry_time", "store_id", "entry_time"),
        Index("ix_track_camera_id_entry_time", "camera_id", "entry_time"),
    )

    def __repr__(self) -> str:
        return f"<Track {self.track_id}>"


# ============================================================================
# Event Model
# ============================================================================
class Event(Base):
    """
    Behavioral event (zone visit, dwell, queue join, etc.).
    
    Attributes:
        id: Unique identifier (UUID)
        event_id: Globally unique event identifier
        event_type: Type of event (from EventType enum)
        store_id: Foreign key to Store
        camera_id: Foreign key to Camera
        track_id: Foreign key to Track
        zone_id: Foreign key to Zone (may be NULL for ENTRY/EXIT)
        visitor_id: FK to Visitor
        timestamp: When event occurred (UTC)
        dwell_ms: Duration of zone dwelling
        queue_depth: Queue depth at event time (for BILLING_QUEUE_JOIN)
        is_staff: Whether person is staff
        confidence: Detection confidence
        metadata: JSON payload with extra fields
        created_at: Record creation timestamp
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    track_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    dwell_ms = Column(Integer, nullable=True)
    queue_depth = Column(Integer, nullable=True)
    is_staff = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    store = relationship("Store", back_populates="events")
    camera = relationship("Camera", back_populates="events")
    track = relationship("Track", back_populates="events")
    zone = relationship("Zone", back_populates="events")
    visitor = relationship("Visitor")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_event_store_timestamp", "store_id", "timestamp"),
        Index("ix_event_track_timestamp", "track_id", "timestamp"),
        Index("ix_event_type_timestamp", "event_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Event {self.event_id}>"


# ============================================================================
# Anomaly Model
# ============================================================================
class Anomaly(Base):
    """
    Detected anomaly in store operations.
    
    Attributes:
        id: Unique identifier (UUID)
        anomaly_id: Globally unique anomaly identifier
        anomaly_type: Type of anomaly (from AnomalyType enum)
        severity: Severity level (from AnomalySeverity enum)
        store_id: Foreign key to Store
        zone_id: Foreign key to Zone (may be NULL for store-level anomalies)
        timestamp: When anomaly was detected
        description: Human-readable description
        value: Numeric value that triggered anomaly
        threshold: Threshold that was exceeded
        is_acknowledged: Whether acknowledged by operator
        acknowledged_at: When anomaly was acknowledged
        suggested_action: Recommended action to take
        metadata: JSON payload with additional context
        created_at: Record creation timestamp
    """
    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    anomaly_id = Column(String(64), unique=True, nullable=False, index=True)
    anomaly_type = Column(SQLEnum(AnomalyType), nullable=False, index=True)
    severity = Column(SQLEnum(AnomalySeverity), nullable=False, index=True)
    store_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    suggested_action = Column(Text, nullable=True)
    anomaly_metadata = Column(JSON, nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    store = relationship("Store", back_populates="anomalies")
    zone = relationship("Zone")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_anomaly_store_timestamp", "store_id", "timestamp"),
        Index("ix_anomaly_severity", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Anomaly {self.anomaly_id}>"
