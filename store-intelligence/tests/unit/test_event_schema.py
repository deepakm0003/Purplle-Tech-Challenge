"""
Unit Tests for Event Schema

Tests Pydantic Event schema validation, serialization,
and adherence to Purplle specification.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from api.schemas import Event, EventType, EventMetadata, EventBatch, EventQuery
from pydantic import ValidationError


class TestEventMetadata:
    """Tests for EventMetadata."""
    
    def test_metadata_initialization(self):
        """Test EventMetadata creation."""
        metadata = EventMetadata(
            queue_depth=5,
            sku_zone="SKINCARE",
            session_seq=3
        )
        
        assert metadata.queue_depth == 5
        assert metadata.sku_zone == "SKINCARE"
        assert metadata.session_seq == 3
        assert metadata.extra == {}
    
    def test_metadata_with_extra(self):
        """Test EventMetadata with extra fields."""
        metadata = EventMetadata(
            queue_depth=2,
            extra={"custom_field": "value", "count": 42}
        )
        
        assert metadata.extra['custom_field'] == "value"
        assert metadata.extra['count'] == 42
    
    def test_metadata_defaults(self):
        """Test EventMetadata default values."""
        metadata = EventMetadata()
        
        assert metadata.queue_depth is None
        assert metadata.sku_zone is None
        assert metadata.session_seq is None
        assert metadata.extra == {}


class TestEventType:
    """Tests for EventType enum."""
    
    def test_all_event_types_exist(self):
        """Test that all 8 event types are defined."""
        expected_types = [
            'ENTRY', 'EXIT', 'ZONE_ENTER', 'ZONE_EXIT',
            'ZONE_DWELL', 'BILLING_QUEUE_JOIN',
            'BILLING_QUEUE_ABANDON', 'REENTRY'
        ]
        
        actual_types = [et.value for et in EventType]
        
        assert len(actual_types) == 8
        for et in expected_types:
            assert et in actual_types
    
    def test_event_type_values(self):
        """Test event type string values."""
        assert EventType.ENTRY.value == "ENTRY"
        assert EventType.EXIT.value == "EXIT"
        assert EventType.ZONE_ENTER.value == "ZONE_ENTER"
        assert EventType.ZONE_EXIT.value == "ZONE_EXIT"
        assert EventType.ZONE_DWELL.value == "ZONE_DWELL"
        assert EventType.BILLING_QUEUE_JOIN.value == "BILLING_QUEUE_JOIN"
        assert EventType.BILLING_QUEUE_ABANDON.value == "BILLING_QUEUE_ABANDON"
        assert EventType.REENTRY.value == "REENTRY"


class TestEvent:
    """Tests for Event schema."""
    
    @pytest.fixture
    def valid_event_dict(self):
        """Create valid event dictionary."""
        return {
            "store_id": "STORE_BLR_001",
            "camera_id": "CAM_001",
            "visitor_id": "VIS_abc123",
            "event_type": EventType.ENTRY,
            "timestamp": datetime.utcnow(),
            "confidence": 0.95
        }
    
    def test_event_creation(self, valid_event_dict):
        """Test Event creation."""
        event = Event(**valid_event_dict)
        
        assert event.store_id == "STORE_BLR_001"
        assert event.camera_id == "CAM_001"
        assert event.visitor_id == "VIS_abc123"
        assert event.event_type == EventType.ENTRY
        assert event.confidence == 0.95
        assert event.event_id is not None
    
    def test_event_auto_generated_id(self, valid_event_dict):
        """Test that event_id is auto-generated."""
        event1 = Event(**valid_event_dict)
        event2 = Event(**valid_event_dict)
        
        assert event1.event_id != event2.event_id
    
    def test_event_default_values(self, valid_event_dict):
        """Test Event default values."""
        event = Event(**valid_event_dict)
        
        assert event.dwell_ms == 0
        assert event.is_staff is False
        assert event.zone_id is None
        assert isinstance(event.metadata, EventMetadata)
    
    def test_event_with_optional_fields(self, valid_event_dict):
        """Test Event with all optional fields."""
        valid_event_dict.update({
            "zone_id": "SKINCARE",
            "dwell_ms": 5000,
            "is_staff": True,
            "metadata": EventMetadata(
                queue_depth=3,
                sku_zone="MOISTURIZER",
                session_seq=5
            )
        })
        
        event = Event(**valid_event_dict)
        
        assert event.zone_id == "SKINCARE"
        assert event.dwell_ms == 5000
        assert event.is_staff is True
        assert event.metadata.queue_depth == 3
    
    def test_event_confidence_validation_low(self, valid_event_dict):
        """Test confidence validation (below 0)."""
        valid_event_dict['confidence'] = -0.1
        
        with pytest.raises(ValidationError):
            Event(**valid_event_dict)
    
    def test_event_confidence_validation_high(self, valid_event_dict):
        """Test confidence validation (above 1)."""
        valid_event_dict['confidence'] = 1.5
        
        with pytest.raises(ValidationError):
            Event(**valid_event_dict)
    
    def test_event_confidence_boundaries(self, valid_event_dict):
        """Test confidence at boundaries."""
        # Test 0
        valid_event_dict['confidence'] = 0.0
        event = Event(**valid_event_dict)
        assert event.confidence == 0.0
        
        # Test 1
        valid_event_dict['confidence'] = 1.0
        event = Event(**valid_event_dict)
        assert event.confidence == 1.0
    
    def test_event_event_id_validation(self, valid_event_dict):
        """Test event_id UUID validation."""
        # Valid UUID
        event_id = str(uuid4())
        valid_event_dict['event_id'] = event_id
        event = Event(**valid_event_dict)
        assert event.event_id == event_id
        
        # Invalid UUID
        valid_event_dict['event_id'] = "not-a-uuid"
        with pytest.raises(ValidationError):
            Event(**valid_event_dict)
    
    def test_event_timestamp_validation(self, valid_event_dict):
        """Test timestamp validation."""
        # Valid datetime
        ts = datetime.utcnow()
        valid_event_dict['timestamp'] = ts
        event = Event(**valid_event_dict)
        assert event.timestamp == ts
        
        # Invalid timestamp (string should work via Pydantic)
        valid_event_dict['timestamp'] = "2026-03-03T14:22:10Z"
        event = Event(**valid_event_dict)
        assert isinstance(event.timestamp, datetime)
    
    def test_event_serialization(self, valid_event_dict):
        """Test Event serialization to dict."""
        event = Event(**valid_event_dict)
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict['store_id'] == "STORE_BLR_001"
        assert event_dict['event_type'] == 'ENTRY'
        assert event_dict['confidence'] == 0.95
        assert 'event_id' in event_dict
        assert isinstance(event_dict['metadata'], dict)
    
    def test_event_timestamp_iso_format(self, valid_event_dict):
        """Test timestamp is ISO format in dict."""
        event = Event(**valid_event_dict)
        event_dict = event.to_dict()
        
        # Should be ISO format string
        assert isinstance(event_dict['timestamp'], str)
        assert 'T' in event_dict['timestamp']
    
    def test_event_schema_example(self):
        """Test event against schema example."""
        # From Pydantic schema
        event = Event(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            store_id="STORE_BLR_002",
            camera_id="CAM_ENTRY_01",
            visitor_id="VIS_c8a2f1",
            event_type=EventType.ZONE_DWELL,
            timestamp=datetime.fromisoformat("2026-03-03T14:22:10"),
            zone_id="SKINCARE",
            dwell_ms=8400,
            is_staff=False,
            confidence=0.91,
            metadata=EventMetadata(sku_zone="MOISTURISER", session_seq=5)
        )
        
        assert event.store_id == "STORE_BLR_002"
        assert event.zone_id == "SKINCARE"
        assert event.dwell_ms == 8400
    
    def test_event_all_event_types(self):
        """Test Event creation with all event types."""
        base_dict = {
            "store_id": "STORE_001",
            "camera_id": "CAM_001",
            "visitor_id": "VIS_001",
            "timestamp": datetime.utcnow(),
            "confidence": 0.9
        }
        
        for event_type in EventType:
            event_dict = base_dict.copy()
            event_dict['event_type'] = event_type
            
            event = Event(**event_dict)
            assert event.event_type == event_type


class TestEventBatch:
    """Tests for EventBatch."""
    
    def test_event_batch_creation(self):
        """Test EventBatch creation."""
        event1 = Event(
            store_id="STORE_001",
            camera_id="CAM_001",
            visitor_id="VIS_001",
            event_type=EventType.ENTRY,
            timestamp=datetime.utcnow(),
            confidence=0.9
        )
        event2 = Event(
            store_id="STORE_001",
            camera_id="CAM_001",
            visitor_id="VIS_002",
            event_type=EventType.EXIT,
            timestamp=datetime.utcnow(),
            confidence=0.85
        )
        
        batch = EventBatch(events=[event1, event2])
        
        assert len(batch.events) == 2
        assert batch.events[0].visitor_id == "VIS_001"
        assert batch.events[1].visitor_id == "VIS_002"


class TestEventQuery:
    """Tests for EventQuery."""
    
    def test_event_query_defaults(self):
        """Test EventQuery with defaults."""
        query = EventQuery()
        
        assert query.store_id is None
        assert query.visitor_id is None
        assert query.event_type is None
        assert query.limit == 100
        assert query.offset == 0
    
    def test_event_query_with_filters(self):
        """Test EventQuery with filters."""
        query = EventQuery(
            store_id="STORE_001",
            visitor_id="VIS_001",
            event_type=EventType.ZONE_ENTER,
            limit=50,
            offset=10
        )
        
        assert query.store_id == "STORE_001"
        assert query.visitor_id == "VIS_001"
        assert query.event_type == EventType.ZONE_ENTER
        assert query.limit == 50
        assert query.offset == 10
    
    def test_event_query_limit_bounds(self):
        """Test EventQuery limit bounds."""
        # Valid high limit
        query = EventQuery(limit=1000)
        assert query.limit == 1000
        
        # Invalid high limit
        with pytest.raises(ValidationError):
            EventQuery(limit=1001)
        
        # Invalid low limit
        with pytest.raises(ValidationError):
            EventQuery(limit=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
