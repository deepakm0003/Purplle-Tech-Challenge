"""
Unit Tests for EventGenerator

Tests event generation for all event types including
validation of schema compliance.
"""

import pytest
from datetime import datetime
from uuid import UUID

from api.schemas import Event, EventType, EventMetadata
from detector.event_generator import EventGenerator
from detector.session_manager import VisitorSession


class TestEventGenerator:
    """Tests for EventGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create EventGenerator instance."""
        return EventGenerator(
            store_id="STORE_TEST_001",
            camera_id="CAM_001"
        )
    
    def test_initialization(self, generator):
        """Test EventGenerator initialization."""
        assert generator.store_id == "STORE_TEST_001"
        assert generator.camera_id == "CAM_001"
        assert len(generator.dwell_last_event) == 0
    
    def test_generate_entry_event(self, generator):
        """Test ENTRY event generation."""
        event = generator.generate_entry_event(
            visitor_id="VIS_123",
            zone_id="ENTRY",
            confidence=0.95
        )
        
        assert isinstance(event, Event)
        assert event.event_type == EventType.ENTRY
        assert event.visitor_id == "VIS_123"
        assert event.zone_id == "ENTRY"
        assert event.dwell_ms == 0
        assert event.confidence == 0.95
        assert event.store_id == "STORE_TEST_001"
        assert event.camera_id == "CAM_001"
        
        # Validate UUID
        UUID(event.event_id)
    
    def test_generate_exit_event(self, generator):
        """Test EXIT event generation."""
        session = VisitorSession("VIS_456", 10)
        session.zones_visited = ["ZONE_A", "ZONE_B"]
        session.exit_time = session.entry_time
        
        event = generator.generate_exit_event(
            session=session,
            confidence=0.92
        )
        
        assert event.event_type == EventType.EXIT
        assert event.visitor_id == "VIS_456"
        assert event.zone_id is None
        assert event.dwell_ms == 0  # Exit time == entry time
        assert event.is_staff is False
        assert event.confidence == 0.92
    
    def test_generate_exit_event_with_dwell(self, generator):
        """Test EXIT event with dwell calculation."""
        from datetime import timedelta
        
        session = VisitorSession("VIS_789", 11)
        session.exit_time = session.entry_time + timedelta(seconds=120)
        
        event = generator.generate_exit_event(session=session)
        
        assert event.dwell_ms == 120000  # 120 seconds = 120000ms
    
    def test_generate_zone_enter_event(self, generator):
        """Test ZONE_ENTER event generation."""
        event = generator.generate_zone_enter_event(
            visitor_id="VIS_111",
            zone_id="SKINCARE",
            session_seq=2,
            confidence=0.88
        )
        
        assert event.event_type == EventType.ZONE_ENTER
        assert event.visitor_id == "VIS_111"
        assert event.zone_id == "SKINCARE"
        assert event.dwell_ms == 0
        assert event.metadata.sku_zone == "SKINCARE"
        assert event.metadata.session_seq == 2
    
    def test_generate_zone_exit_event(self, generator):
        """Test ZONE_EXIT event generation."""
        event = generator.generate_zone_exit_event(
            visitor_id="VIS_222",
            zone_id="COSMETICS",
            dwell_ms=5000,
            session_seq=3,
            confidence=0.87
        )
        
        assert event.event_type == EventType.ZONE_EXIT
        assert event.zone_id == "COSMETICS"
        assert event.dwell_ms == 5000
        assert event.metadata.sku_zone == "COSMETICS"
        assert event.metadata.session_seq == 3
    
    def test_generate_zone_dwell_event_first_time(self, generator):
        """Test first ZONE_DWELL event (always emitted)."""
        event = generator.generate_zone_dwell_event(
            visitor_id="VIS_333",
            zone_id="BILLING",
            dwell_ms=2000,
            session_seq=5,
            confidence=0.90
        )
        
        assert event is not None
        assert event.event_type == EventType.ZONE_DWELL
        assert event.zone_id == "BILLING"
        assert event.dwell_ms == 2000
        assert event.metadata.session_seq == 5
    
    def test_generate_zone_dwell_event_throttled(self, generator):
        """Test ZONE_DWELL throttling (should skip second event too soon)."""
        visitor_id = "VIS_444"
        
        # First DWELL event
        event1 = generator.generate_zone_dwell_event(
            visitor_id=visitor_id,
            zone_id="BILLING",
            dwell_ms=1000
        )
        assert event1 is not None
        
        # Second DWELL event immediately after (should be throttled)
        event2 = generator.generate_zone_dwell_event(
            visitor_id=visitor_id,
            zone_id="BILLING",
            dwell_ms=2000
        )
        assert event2 is None
    
    def test_generate_billing_queue_join_event(self, generator):
        """Test BILLING_QUEUE_JOIN event generation."""
        event = generator.generate_billing_queue_join_event(
            visitor_id="VIS_555",
            queue_depth=3,
            session_seq=7,
            confidence=0.85
        )
        
        assert event.event_type == EventType.BILLING_QUEUE_JOIN
        assert event.zone_id == "BILLING"
        assert event.metadata.queue_depth == 3
        assert event.metadata.session_seq == 7
    
    def test_generate_billing_queue_abandon_event(self, generator):
        """Test BILLING_QUEUE_ABANDON event generation."""
        event = generator.generate_billing_queue_abandon_event(
            visitor_id="VIS_666",
            session_seq=8,
            confidence=0.91
        )
        
        assert event.event_type == EventType.BILLING_QUEUE_ABANDON
        assert event.zone_id == "BILLING"
        assert event.metadata.session_seq == 8
    
    def test_generate_reentry_event(self, generator):
        """Test REENTRY event generation."""
        event = generator.generate_reentry_event(
            visitor_id="VIS_777",
            reentry_count=2,
            session_seq=1,
            confidence=0.93
        )
        
        assert event.event_type == EventType.REENTRY
        assert event.zone_id == "ENTRY"
        assert event.metadata.extra['reentry_count'] == 2
        assert event.metadata.session_seq == 1
    
    def test_event_uuid_uniqueness(self, generator):
        """Test that each generated event has unique UUID."""
        event1 = generator.generate_entry_event("VIS_A")
        event2 = generator.generate_entry_event("VIS_B")
        
        assert event1.event_id != event2.event_id
        
        # Both should be valid UUIDs
        UUID(event1.event_id)
        UUID(event2.event_id)
    
    def test_event_schema_validation(self, generator):
        """Test that generated events pass Pydantic validation."""
        event = generator.generate_zone_enter_event(
            visitor_id="VIS_999",
            zone_id="TEST_ZONE",
            confidence=0.75
        )
        
        # Should be valid per Pydantic model
        assert event.confidence >= 0 and event.confidence <= 1
        assert isinstance(event.timestamp, datetime)
        assert event.store_id == "STORE_TEST_001"
    
    def test_event_serialization(self, generator):
        """Test that events can be serialized to dict."""
        event = generator.generate_entry_event("VIS_001")
        
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict['event_type'] == 'ENTRY'
        assert event_dict['visitor_id'] == 'VIS_001'
        assert 'event_id' in event_dict
        assert 'timestamp' in event_dict
        assert isinstance(event_dict['metadata'], dict)
    
    def test_reset(self, generator):
        """Test resetting generator state."""
        # Emit a dwell event to populate state
        generator.generate_zone_dwell_event(
            visitor_id="VIS_reset",
            zone_id="TEST"
        )
        
        assert len(generator.dwell_last_event) > 0
        
        generator.reset()
        
        assert len(generator.dwell_last_event) == 0
    
    def test_all_event_types_generation(self, generator):
        """Test that all 8 event types can be generated."""
        session = VisitorSession("VIS_test", 1)
        
        events = [
            generator.generate_entry_event("VIS_test"),
            generator.generate_zone_enter_event("VIS_test", "ZONE_A"),
            generator.generate_zone_dwell_event("VIS_test", "ZONE_A", 1000),
            generator.generate_zone_exit_event("VIS_test", "ZONE_A", 1000),
            generator.generate_billing_queue_join_event("VIS_test", 1),
            generator.generate_billing_queue_abandon_event("VIS_test"),
            generator.generate_reentry_event("VIS_test"),
            generator.generate_exit_event(session),
        ]
        
        event_types = {e.event_type for e in events if e is not None}
        
        assert len(event_types) == 8
        for et in EventType:
            assert et in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
