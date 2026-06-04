"""
Unit Tests for MetricsEngine.

Test coverage:
- Unique visitor counting
- Conversion rate
- Dwell time calculations
- Queue metrics
- Zone-based metrics
- Edge cases (zero visitors, empty events)
- Staff exclusion
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from api.schemas import Event, EventType, EventMetadata
from analytics.conversion_engine import ConversionEngine, ConversionMatch
from analytics.metrics import MetricsEngine, create_metrics_engine


class TestMetricsEngineSetup:
    """Test MetricsEngine initialization."""
    
    def test_engine_creation(self):
        """Test creating MetricsEngine."""
        engine = MetricsEngine()
        assert engine is not None
        assert len(engine.events) == 0
    
    def test_factory_function(self):
        """Test factory function."""
        engine = create_metrics_engine()
        assert engine is not None


class TestMetricsEngineVisitors:
    """Test visitor-related metrics."""
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        return [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ENTRY,
                timestamp=base_time,
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=30),
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",  # Duplicate visitor
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=60),
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_STAFF",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=90),
                zone_id=None,
                dwell_ms=0,
                is_staff=True,  # Staff member
                confidence=0.95
            ),
        ]
    
    def test_unique_visitors_excludes_staff(self, sample_events):
        """Test that staff are excluded from visitor count."""
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(sample_events, conversion_engine)
        
        # Should be 2 unique visitors (VIS_001, VIS_002) excluding staff
        assert metrics['unique_visitors'] == 2
    
    def test_footfall_count(self, sample_events):
        """Test footfall counting."""
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(sample_events, conversion_engine)
        
        # Footfall should be 2 (two ENTRY events from non-staff)
        assert metrics['store_footfall'] == 2


class TestMetricsEngineDwellTime:
    """Test dwell time calculations."""
    
    def test_average_dwell_time(self):
        """Test average dwell time from EXIT events."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.EXIT,
                timestamp=base_time,
                zone_id=None,
                dwell_ms=600000,  # 10 minutes = 600 seconds
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.EXIT,
                timestamp=base_time + timedelta(seconds=1),
                zone_id=None,
                dwell_ms=420000,  # 7 minutes = 420 seconds
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # Average should be (600 + 420) / 2 = 510 seconds
        assert metrics['average_dwell_time'] == 510
    
    def test_dwell_by_zone(self):
        """Test dwell time per zone."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time,
                zone_id="SKINCARE",
                dwell_ms=300000,  # 5 minutes
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=1),
                zone_id="SKINCARE",
                dwell_ms=120000,  # 2 minutes
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=2),
                zone_id="COSMETICS",
                dwell_ms=180000,  # 3 minutes
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # SKINCARE: (300 + 120) / 2 = 210 seconds
        assert metrics['average_dwell_by_zone']['SKINCARE'] == 210
        # COSMETICS: 180 seconds
        assert metrics['average_dwell_by_zone']['COSMETICS'] == 180


class TestMetricsEngineQueue:
    """Test queue-related metrics."""
    
    def test_queue_depth_peak(self):
        """Test peak queue depth."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95,
                metadata=EventMetadata(queue_depth=5)
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=10),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95,
                metadata=EventMetadata(queue_depth=12)
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # Peak should be 12
        assert metrics['queue_depth'] == 12
    
    def test_abandonment_rate(self):
        """Test queue abandonment rate."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=5),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_003",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=10),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_ABANDON,
                timestamp=base_time + timedelta(seconds=20),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # 1 abandon / 3 joins = 0.333...
        assert metrics['abandonment_rate'] == pytest.approx(1/3, rel=0.01)


class TestMetricsEngineConversion:
    """Test conversion-related metrics."""
    
    def test_conversion_rate_with_matches(self):
        """Test conversion rate from matched transactions."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ENTRY,
                timestamp=base_time,
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=30),
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        # Manually create conversions
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id="VIS_001",
                transaction_id="TXN_001",
                event_timestamp=base_time,
                transaction_timestamp=base_time + timedelta(seconds=60),
                basket_value=5000.0,
                confidence=0.95
            )
        ]
        
        engine = MetricsEngine()
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # 1 conversion / 2 entries = 0.5
        assert metrics['conversion_rate'] == 0.5
    
    def test_revenue_and_basket(self):
        """Test revenue and basket size metrics."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        events = []
        
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id="VIS_001",
                transaction_id="TXN_001",
                event_timestamp=base_time,
                transaction_timestamp=base_time + timedelta(seconds=60),
                basket_value=5000.0,
                confidence=0.95
            ),
            ConversionMatch(
                visitor_id="VIS_002",
                transaction_id="TXN_002",
                event_timestamp=base_time,
                transaction_timestamp=base_time + timedelta(seconds=90),
                basket_value=3000.0,
                confidence=0.90
            ),
        ]
        
        engine = MetricsEngine()
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # Total revenue = 8000
        assert metrics['revenue'] == 8000.0
        # Average basket = 8000 / 2 = 4000
        assert metrics['average_basket_size'] == 4000.0


class TestMetricsEngineZoneVisits:
    """Test zone-based metrics."""
    
    def test_zone_visit_frequency(self):
        """Test zone visit frequency counting."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time,
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=30),
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=60),
                zone_id="COSMETICS",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # SKINCARE: 2 visits, COSMETICS: 1 visit
        assert metrics['zone_visit_frequency']['SKINCARE'] == 2
        assert metrics['zone_visit_frequency']['COSMETICS'] == 1


class TestMetricsEngineEdgeCases:
    """Test edge cases."""
    
    def test_no_events(self):
        """Test with no events."""
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics([], conversion_engine)
        
        assert metrics['unique_visitors'] == 0
        assert metrics['store_footfall'] == 0
        assert metrics['conversion_rate'] == 0.0
        assert metrics['revenue'] == 0.0
    
    def test_all_staff_events(self):
        """Test when all events are from staff."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_STAFF",
                event_type=EventType.ENTRY,
                timestamp=base_time,
                zone_id=None,
                dwell_ms=0,
                is_staff=True,
                confidence=0.95
            ),
        ]
        
        engine = MetricsEngine()
        conversion_engine = ConversionEngine()
        
        metrics = engine.compute_metrics(events, conversion_engine)
        
        # All staff should be excluded
        assert metrics['unique_visitors'] == 0
        assert metrics['store_footfall'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
