"""
Event Generation Module.

Generates structured behavioral events from tracked visitors,
zone transitions, and session lifecycle.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType, EventMetadata
from detector.session_manager import VisitorSession


class EventGenerator:
    """
    Generates retail events from tracking and session data.
    
    Converts low-level tracking information into high-level
    business events per Purplle specification.
    """
    
    # Event generation configuration
    DWELL_INTERVAL_SECONDS = 30  # Emit ZONE_DWELL every N seconds
    
    def __init__(
        self,
        store_id: str,
        camera_id: str
    ):
        """
        Initialize event generator.
        
        Args:
            store_id: Store identifier
            camera_id: Camera identifier
        """
        self.store_id = store_id
        self.camera_id = camera_id
        self.dwell_last_event: Dict[str, float] = {}  # visitor_id -> last dwell event time
        
        logger.info(f"EventGenerator init: store={store_id}, camera={camera_id}")
    
    def generate_entry_event(
        self,
        visitor_id: str,
        zone_id: str = "ENTRY",
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9
    ) -> Event:
        """
        Generate ENTRY event for store entry.
        
        Args:
            visitor_id: Visitor identifier
            zone_id: Entry zone (default "ENTRY")
            timestamp: Event timestamp (default now)
            confidence: Detection confidence
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.ENTRY,
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=0,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(session_seq=1)
        )
        
        logger.debug(f"Generated ENTRY event for {visitor_id}")
        return event
    
    def generate_exit_event(
        self,
        session: VisitorSession,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9
    ) -> Event:
        """
        Generate EXIT event for store exit.
        
        Args:
            session: VisitorSession object
            timestamp: Event timestamp (default now)
            confidence: Detection confidence
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Calculate total dwell time
        if session.exit_time:
            dwell_ms = int((session.exit_time - session.entry_time).total_seconds() * 1000)
        else:
            dwell_ms = int((timestamp - session.entry_time).total_seconds() * 1000)
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=session.visitor_id,
            event_type=EventType.EXIT,
            timestamp=timestamp,
            zone_id=None,  # EXIT has no zone
            dwell_ms=dwell_ms,
            is_staff=session.is_staff,
            confidence=confidence,
            metadata=EventMetadata(
                session_seq=len(session.zones_visited) + 1
            )
        )
        
        logger.debug(f"Generated EXIT event for {session.visitor_id}, dwell={dwell_ms}ms")
        return event
    
    def generate_zone_enter_event(
        self,
        visitor_id: str,
        zone_id: str,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 0
    ) -> Event:
        """
        Generate ZONE_ENTER event.
        
        Args:
            visitor_id: Visitor identifier
            zone_id: Zone being entered
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.ZONE_ENTER,
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=0,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(
                sku_zone=zone_id,
                session_seq=session_seq
            )
        )
        
        logger.debug(f"Generated ZONE_ENTER event: {visitor_id} -> {zone_id}")
        return event
    
    def generate_zone_exit_event(
        self,
        visitor_id: str,
        zone_id: str,
        dwell_ms: int = 0,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 0
    ) -> Event:
        """
        Generate ZONE_EXIT event.
        
        Args:
            visitor_id: Visitor identifier
            zone_id: Zone being exited
            dwell_ms: Dwell time in zone
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.ZONE_EXIT,
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(
                sku_zone=zone_id,
                session_seq=session_seq
            )
        )
        
        logger.debug(f"Generated ZONE_EXIT event: {visitor_id} from {zone_id}, dwell={dwell_ms}ms")
        return event
    
    def generate_zone_dwell_event(
        self,
        visitor_id: str,
        zone_id: str,
        dwell_ms: int,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 0
    ) -> Optional[Event]:
        """
        Generate ZONE_DWELL event (periodic, every 30 seconds).
        
        Args:
            visitor_id: Visitor identifier
            zone_id: Zone for dwell
            dwell_ms: Total dwell time in zone
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event or None if too soon since last dwell event
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Check if enough time has passed since last dwell event
        last_time = self.dwell_last_event.get(visitor_id, 0)
        current_time = timestamp.timestamp()
        
        if current_time - last_time < self.DWELL_INTERVAL_SECONDS:
            return None
        
        self.dwell_last_event[visitor_id] = current_time
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.ZONE_DWELL,
            timestamp=timestamp,
            zone_id=zone_id,
            dwell_ms=dwell_ms,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(
                sku_zone=zone_id,
                session_seq=session_seq
            )
        )
        
        logger.debug(f"Generated ZONE_DWELL event: {visitor_id} in {zone_id}, {dwell_ms}ms")
        return event
    
    def generate_billing_queue_join_event(
        self,
        visitor_id: str,
        queue_depth: int,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 0
    ) -> Event:
        """
        Generate BILLING_QUEUE_JOIN event.
        
        Args:
            visitor_id: Visitor identifier
            queue_depth: Current queue depth
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.BILLING_QUEUE_JOIN,
            timestamp=timestamp,
            zone_id="BILLING",
            dwell_ms=0,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(
                queue_depth=queue_depth,
                session_seq=session_seq
            )
        )
        
        logger.debug(f"Generated BILLING_QUEUE_JOIN event: {visitor_id}, depth={queue_depth}")
        return event
    
    def generate_billing_queue_abandon_event(
        self,
        visitor_id: str,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 0
    ) -> Event:
        """
        Generate BILLING_QUEUE_ABANDON event.
        
        Args:
            visitor_id: Visitor identifier
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.BILLING_QUEUE_ABANDON,
            timestamp=timestamp,
            zone_id="BILLING",
            dwell_ms=0,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(session_seq=session_seq)
        )
        
        logger.debug(f"Generated BILLING_QUEUE_ABANDON event: {visitor_id}")
        return event
    
    def generate_reentry_event(
        self,
        visitor_id: str,
        reentry_count: int = 1,
        timestamp: Optional[datetime] = None,
        confidence: float = 0.9,
        session_seq: int = 1
    ) -> Event:
        """
        Generate REENTRY event for returning visitor.
        
        Args:
            visitor_id: Visitor identifier
            reentry_count: Number of times re-entered
            timestamp: Event timestamp
            confidence: Detection confidence
            session_seq: Session sequence number
            
        Returns:
            Generated Event
        """
        timestamp = timestamp or datetime.utcnow()
        
        event = Event(
            event_id=str(uuid.uuid4()),
            store_id=self.store_id,
            camera_id=self.camera_id,
            visitor_id=visitor_id,
            event_type=EventType.REENTRY,
            timestamp=timestamp,
            zone_id="ENTRY",
            dwell_ms=0,
            is_staff=False,
            confidence=confidence,
            metadata=EventMetadata(
                extra={'reentry_count': reentry_count},
                session_seq=session_seq
            )
        )
        
        logger.debug(f"Generated REENTRY event: {visitor_id}, count={reentry_count}")
        return event
    
    def reset(self) -> None:
        """Reset state."""
        self.dwell_last_event.clear()
        logger.info("EventGenerator reset")

