"""
Unit Tests for FunnelEngine.

Test coverage:
- Funnel stage tracking (Entry → Zone → Billing → Purchase)
- Dropoff percentage calculations
- No double-counting
- Efficiency metrics
- Edge cases (empty funnel, no conversions)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from api.schemas import Event, EventType, EventMetadata
from analytics.conversion_engine import ConversionEngine, ConversionMatch
from analytics.funnel import FunnelEngine, create_funnel_engine


class TestFunnelEngineSetup:
    """Test FunnelEngine initialization."""
    
    def test_engine_creation(self):
        """Test creating FunnelEngine."""
        engine = FunnelEngine()
        assert engine is not None
        assert len(engine.stages['entry']) == 0
    
    def test_factory_function(self):
        """Test factory function."""
        engine = create_funnel_engine()
        assert engine is not None


class TestFunnelEngineTracking:
    """Test funnel stage tracking."""
    
    def test_complete_funnel_journey(self):
        """Test complete journey through all funnel stages."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # Stage 1: Entry
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
            # Stage 2: Zone Visit
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=60),
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            # Stage 3: Billing Queue
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=120),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        # Stage 4: Purchase (via conversion)
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id="VIS_001",
                transaction_id="TXN_001",
                event_timestamp=base_time + timedelta(seconds=120),
                transaction_timestamp=base_time + timedelta(seconds=150),

                basket_value=5000.0,
                confidence=0.95
            )
        ]
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        assert funnel['entry_count'] == 1
        assert funnel['zone_count'] == 1
        assert funnel['billing_count'] == 1
        assert funnel['purchase_count'] == 1
    
    def test_partial_funnel_journey(self):
        """Test journey that doesn't complete all stages."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # Stage 1: Entry
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
            # Stage 2: Zone Visit
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=60),
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            # No billing or purchase
        ]
        
        conversion_engine = ConversionEngine()
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        assert funnel['entry_count'] == 1
        assert funnel['zone_count'] == 1
        assert funnel['billing_count'] == 0
        assert funnel['purchase_count'] == 0
    
    def test_multiple_visitors_different_stages(self):
        """Test multiple visitors at different stages."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # VIS_001: Complete journey
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
                visitor_id="VIS_001",
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
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=120),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            
            # VIS_002: Entry + Zone only
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=10),
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
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=70),
                zone_id="COSMETICS",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            
            # VIS_003: Entry only
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_003",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=20),
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id="VIS_001",
                transaction_id="TXN_001",
                event_timestamp=base_time + timedelta(seconds=120),
                transaction_timestamp=base_time + timedelta(seconds=150),
                basket_value=5000.0,
                confidence=0.95
            )
        ]
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        assert funnel['entry_count'] == 3
        assert funnel['zone_count'] == 2
        assert funnel['billing_count'] == 1
        assert funnel['purchase_count'] == 1


class TestFunnelEngineDropoff:
    """Test dropoff percentage calculations."""
    
    def test_entry_to_zone_dropoff(self):
        """Test dropoff from entry to zone."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # 10 entries
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_{i:03d}",
                    event_type=EventType.ENTRY,
                    timestamp=base_time + timedelta(seconds=i*10),
                    zone_id=None,
                    dwell_ms=0,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(10)
            ],
            # 7 zone visits
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_{i:03d}",
                    event_type=EventType.ZONE_ENTER,
                    timestamp=base_time + timedelta(seconds=i*10 + 30),
                    zone_id="SKINCARE",
                    dwell_ms=0,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(7)
            ],
        ]
        
        conversion_engine = ConversionEngine()
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        # (10 - 7) / 10 * 100 = 30% dropoff
        assert funnel['dropoff_percentages']['entry_to_zone'] == 30.0
    
    def test_zero_dropoff_all_complete(self):
        """Test zero dropoff when all visitors complete stage."""
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
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(seconds=30),
                zone_id="SKINCARE",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        conversion_engine = ConversionEngine()
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        # No dropoff from entry to zone (1 entry, 1 zone)
        assert funnel['dropoff_percentages']['entry_to_zone'] == 0.0
    
    def test_overall_conversion_rate(self):
        """Test overall conversion dropoff."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_{i:03d}",
                    event_type=EventType.ENTRY,
                    timestamp=base_time + timedelta(seconds=i*10),
                    zone_id=None,
                    dwell_ms=0,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(100)
            ],
        ]
        
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id=f"VIS_{i:03d}",
                transaction_id=f"TXN_{i:03d}",
                event_timestamp=base_time,
                transaction_timestamp=base_time + timedelta(seconds=60),

                basket_value=5000.0,
                confidence=0.95
            )
            for i in range(10)  # Only 10 purchases
        ]
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        # (100 - 10) / 100 * 100 = 90% overall dropoff
        assert funnel['dropoff_percentages']['overall_conversion'] == 90.0


class TestFunnelEngineEfficiency:
    """Test efficiency calculations."""
    
    def test_funnel_efficiency(self):
        """Test overall funnel efficiency."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_{i:03d}",
                    event_type=EventType.ENTRY,
                    timestamp=base_time + timedelta(seconds=i*10),
                    zone_id=None,
                    dwell_ms=0,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(100)
            ],
        ]
        
        conversion_engine = ConversionEngine()
        conversion_engine.conversions = [
            ConversionMatch(
                visitor_id=f"VIS_{i:03d}",
                transaction_id=f"TXN_{i:03d}",
                event_timestamp=base_time,
                transaction_timestamp=base_time + timedelta(seconds=60),
                basket_value=5000.0,
                confidence=0.95
            )
            for i in range(20)  # 20 purchases
        ]
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        # Efficiency = (20 / 100) * 100 = 20%
        assert funnel['efficiency_percentage'] == 20.0


class TestFunnelEngineStaffExclusion:
    """Test staff exclusion."""
    
    def test_staff_excluded_from_funnel(self):
        """Test that staff visitors are excluded."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # Regular visitor
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
            # Staff visitor
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_STAFF",
                event_type=EventType.ENTRY,
                timestamp=base_time + timedelta(seconds=10),
                zone_id=None,
                dwell_ms=0,
                is_staff=True,
                confidence=0.95
            ),
        ]
        
        conversion_engine = ConversionEngine()
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel(events, conversion_engine)
        
        # Only 1 entry (staff excluded)
        assert funnel['entry_count'] == 1


class TestFunnelEngineEdgeCases:
    """Test edge cases."""
    
    def test_empty_funnel(self):
        """Test with no events."""
        conversion_engine = ConversionEngine()
        
        engine = FunnelEngine()
        funnel = engine.compute_funnel([], conversion_engine)
        
        assert funnel['entry_count'] == 0
        assert funnel['zone_count'] == 0
        assert funnel['billing_count'] == 0
        assert funnel['purchase_count'] == 0
    
    def test_get_stats(self):
        """Test get_stats method."""
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
        ]
        
        conversion_engine = ConversionEngine()
        engine = FunnelEngine()
        engine.compute_funnel(events, conversion_engine)
        
        stats = engine.get_stats()
        
        assert stats['total_entry'] == 1
        assert 'efficiency_percentage' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
