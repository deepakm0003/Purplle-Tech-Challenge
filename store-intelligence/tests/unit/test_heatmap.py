"""
Unit Tests for HeatmapEngine.

Test coverage:
- Zone heatmap data generation
- Normalized heat scores (0-100)
- Visit frequency and dwell time per zone
- Data confidence levels (HIGH/LOW)
- Hottest/coldest zones
- Edge cases (empty zones, no data)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from api.schemas import Event, EventType
from analytics.heatmap import HeatmapEngine, HeatmapZone, create_heatmap_engine


class TestHeatmapZone:
    """Test HeatmapZone dataclass."""
    
    def test_zone_creation(self):
        """Test creating a HeatmapZone."""
        zone = HeatmapZone("SKINCARE")
        assert zone.zone_id == "SKINCARE"
        assert zone.visit_count == 0
    
    def test_zone_add_visit(self):
        """Test adding visits to zone."""
        zone = HeatmapZone("SKINCARE")
        zone.add_visit(300000)  # 5 minutes
        
        assert zone.visit_count == 1
        assert zone.total_dwell_ms == 300000
    
    def test_zone_avg_dwell(self):
        """Test average dwell calculation."""
        zone = HeatmapZone("SKINCARE")
        zone.add_visit(300000)  # 5 minutes
        zone.add_visit(120000)  # 2 minutes
        
        avg = zone.get_avg_dwell()
        # (300000 + 120000) / 2 / 1000 = 210 seconds
        assert avg == 210
    
    def test_zone_to_dict(self):
        """Test converting zone to dictionary."""
        zone = HeatmapZone("SKINCARE")
        zone.add_visit(300000)
        
        d = zone.to_dict()
        assert d['zone_id'] == "SKINCARE"
        assert d['visit_frequency'] == 1
        assert d['avg_dwell_seconds'] == 300


class TestHeatmapEngineSetup:
    """Test HeatmapEngine initialization."""
    
    def test_engine_creation(self):
        """Test creating HeatmapEngine."""
        engine = HeatmapEngine()
        assert engine is not None
        assert len(engine.zones) == 0
    
    def test_factory_function(self):
        """Test factory function."""
        engine = create_heatmap_engine()
        assert engine is not None


class TestHeatmapEngineGeneration:
    """Test heatmap generation."""
    
    def test_basic_heatmap_generation(self):
        """Test basic heatmap generation."""
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
                visitor_id="VIS_002",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=1),
                zone_id="COSMETICS",
                dwell_ms=180000,  # 3 minutes
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        assert heatmap['zone_count'] == 2
        assert heatmap['total_sessions'] == 2
        assert len(heatmap['zones']) == 2
    
    def test_normalized_heat_scores(self):
        """Test that heat scores are normalized 0-100."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # Zone 1: 10 visits
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=i),
                    zone_id="ZONE1",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(10)
            ],
            # Zone 2: 5 visits
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_B{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=10 + i),
                    zone_id="ZONE2",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(5)
            ],
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        # Find zones in result
        zone1 = next((z for z in heatmap['zones'] if z['zone_id'] == 'ZONE1'), None)
        zone2 = next((z for z in heatmap['zones'] if z['zone_id'] == 'ZONE2'), None)
        
        assert zone1 is not None
        assert zone2 is not None
        assert zone1['normalized_heat_score'] == 100.0  # Max visits
        assert zone2['normalized_heat_score'] == 50.0   # Half of max


class TestHeatmapEngineDataConfidence:
    """Test data confidence levels."""
    
    def test_low_confidence_threshold(self):
        """Test LOW confidence when sessions < 20."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id=f"VIS_{i}",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=i),
                zone_id="ZONE1",
                dwell_ms=300000,
                is_staff=False,
                confidence=0.95
            )
            for i in range(10)  # Only 10 sessions
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        assert heatmap['data_confidence'] == 'LOW'
    
    def test_high_confidence_threshold(self):
        """Test HIGH confidence when sessions >= 20."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id=f"VIS_{i}",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=i),
                zone_id="ZONE1",
                dwell_ms=300000,
                is_staff=False,
                confidence=0.95
            )
            for i in range(20)  # Exactly 20 sessions
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        assert heatmap['data_confidence'] == 'HIGH'


class TestHeatmapEngineHotCold:
    """Test hottest/coldest zone methods."""
    
    def test_get_hottest_zones(self):
        """Test getting hottest zones."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_A{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=i),
                    zone_id="ZONE1",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(30)
            ],
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_B{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=100 + i),
                    zone_id="ZONE2",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(10)
            ],
        ]
        
        engine = HeatmapEngine()
        engine.compute_heatmap(events)
        
        hottest = engine.get_hottest_zones(top_n=1)
        
        assert len(hottest) == 1
        assert hottest[0]['zone_id'] == 'ZONE1'  # Most visits
    
    def test_get_coldest_zones(self):
        """Test getting coldest zones."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_A{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=i),
                    zone_id="ZONE1",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(30)
            ],
            *[
                Event(
                    event_id=str(uuid4()),
                    store_id="STORE_001",
                    camera_id="CAM_001",
                    visitor_id=f"VIS_B{i}",
                    event_type=EventType.ZONE_EXIT,
                    timestamp=base_time + timedelta(seconds=100 + i),
                    zone_id="ZONE2",
                    dwell_ms=300000,
                    is_staff=False,
                    confidence=0.95
                )
                for i in range(5)
            ],
        ]
        
        engine = HeatmapEngine()
        engine.compute_heatmap(events)
        
        coldest = engine.get_coldest_zones(bottom_n=1)
        
        assert len(coldest) == 1
        assert coldest[0]['zone_id'] == 'ZONE2'  # Least visits


class TestHeatmapEngineDwellTime:
    """Test dwell time calculations."""
    
    def test_zone_average_dwell(self):
        """Test average dwell time per zone."""
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
                visitor_id="VIS_002",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=1),
                zone_id="SKINCARE",
                dwell_ms=120000,  # 2 minutes
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        zone = next((z for z in heatmap['zones'] if z['zone_id'] == 'SKINCARE'), None)
        
        assert zone is not None
        # (300 + 120) / 2 = 210 seconds
        assert zone['avg_dwell_seconds'] == 210


class TestHeatmapEngineStaffExclusion:
    """Test staff exclusion."""
    
    def test_staff_excluded_from_heatmap(self):
        """Test that staff visits are excluded."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            # Regular visitor
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time,
                zone_id="SKINCARE",
                dwell_ms=300000,
                is_staff=False,
                confidence=0.95
            ),
            # Staff visitor
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_STAFF",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time + timedelta(seconds=1),
                zone_id="SKINCARE",
                dwell_ms=300000,
                is_staff=True,
                confidence=0.95
            ),
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        # Only 1 visit (staff excluded)
        zone = next((z for z in heatmap['zones'] if z['zone_id'] == 'SKINCARE'), None)
        assert zone['visit_frequency'] == 1


class TestHeatmapEngineEdgeCases:
    """Test edge cases."""
    
    def test_empty_heatmap(self):
        """Test with no events."""
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap([])
        
        assert heatmap['zone_count'] == 0
        assert heatmap['total_sessions'] == 0
        assert len(heatmap['zones']) == 0
    
    def test_zone_dwell_events(self):
        """Test processing ZONE_DWELL events."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_DWELL,
                timestamp=base_time,
                zone_id="SKINCARE",
                dwell_ms=300000,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = HeatmapEngine()
        heatmap = engine.compute_heatmap(events)
        
        # Should process ZONE_DWELL events
        assert heatmap['zone_count'] >= 1
    
    def test_get_stats(self):
        """Test get_stats method."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_EXIT,
                timestamp=base_time,
                zone_id="ZONE1",
                dwell_ms=300000,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        engine = HeatmapEngine()
        engine.compute_heatmap(events)
        
        stats = engine.get_stats()
        
        assert stats['total_zones'] == 1
        assert stats['total_visits'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
