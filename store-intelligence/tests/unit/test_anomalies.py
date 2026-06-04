"""
Unit Tests for AnomalyDetector.

Test coverage:
- Queue spike detection
- Conversion drop detection
- Dead zone detection
- Severity levels (INFO, WARNING, CRITICAL)
- Anomaly filtering and statistics
- Edge cases (no data, no anomalies)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from api.schemas import Event, EventType, EventMetadata
from analytics.anomalies import AnomalyDetector, Anomaly, AnomalySeverity, create_anomaly_detector


class TestAnomalyCreation:
    """Test Anomaly dataclass."""
    
    def test_anomaly_creation(self):
        """Test creating an Anomaly."""
        anomaly = Anomaly(
            anomaly_type="QUEUE_SPIKE",
            severity=AnomalySeverity.WARNING,
            description="Queue is spiking",
            metric_value=15.0,
            threshold=10.0,
            suggested_action="Open new checkout"
        )
        
        assert anomaly.anomaly_type == "QUEUE_SPIKE"
        assert anomaly.severity == AnomalySeverity.WARNING
        assert anomaly.metric_value == 15.0
    
    def test_anomaly_to_dict(self):
        """Test converting anomaly to dictionary."""
        anomaly = Anomaly(
            anomaly_type="QUEUE_SPIKE",
            severity=AnomalySeverity.WARNING,
            description="Queue is spiking",
            metric_value=15.0,
            threshold=10.0,
            suggested_action="Open new checkout"
        )
        
        d = anomaly.to_dict()
        
        assert d['anomaly_type'] == "QUEUE_SPIKE"
        assert d['severity'] == "WARNING"
        assert 'detected_at' in d


class TestAnomalyDetectorSetup:
    """Test AnomalyDetector initialization."""
    
    def test_detector_creation(self):
        """Test creating AnomalyDetector."""
        detector = AnomalyDetector()
        assert detector is not None
        assert len(detector.anomalies) == 0
    
    def test_factory_function(self):
        """Test factory function."""
        detector = create_anomaly_detector()
        assert detector is not None


class TestQueueSpikeDetection:
    """Test queue spike anomaly detection."""
    
    def test_queue_spike_detected(self):
        """Test detecting a queue spike."""
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
                metadata=EventMetadata(queue_depth=15)  # Spike
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_queue_average=5.0)
        
        # Should detect spike (15 > 5 * 1.5)
        assert len(detector.anomalies) > 0
        queue_spikes = [a for a in detector.anomalies if a.anomaly_type == "QUEUE_SPIKE"]
        assert len(queue_spikes) > 0
    
    def test_no_queue_spike_within_threshold(self):
        """Test no spike when within threshold."""
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
                metadata=EventMetadata(queue_depth=7)  # Within threshold
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_queue_average=5.0)
        
        queue_spikes = [a for a in detector.anomalies if a.anomaly_type == "QUEUE_SPIKE"]
        assert len(queue_spikes) == 0
    
    def test_queue_spike_critical_severity(self):
        """Test CRITICAL severity for large spike."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id=f"VIS_{i}",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=i),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95,
                metadata=EventMetadata(queue_depth=i + 20)  # Up to 20+
            )
            for i in range(5)
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_queue_average=5.0)
        
        critical = [a for a in detector.anomalies if a.severity == AnomalySeverity.CRITICAL]
        assert len(critical) > 0


class TestConversionDropDetection:
    """Test conversion drop anomaly detection."""
    
    def test_conversion_drop_detected(self):
        """Test detecting a conversion drop."""
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
                timestamp=base_time + timedelta(seconds=1),
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        # Historical: 50% conversion, current: 10% (40% drop)
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_conversion_rate=0.5)
        
        drops = [a for a in detector.anomalies if a.anomaly_type == "CONVERSION_DROP"]
        assert len(drops) > 0
    
    def test_no_conversion_drop_within_threshold(self):
        """Test no drop when within threshold."""
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
        
        # Historical: 50%, current: 40% (only 20% drop, threshold is 25%)
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_conversion_rate=0.5)
        
        drops = [a for a in detector.anomalies if a.anomaly_type == "CONVERSION_DROP"]
        assert len(drops) == 0


class TestDeadZoneDetection:
    """Test dead zone anomaly detection."""
    
    def test_dead_zone_detected(self):
        """Test detecting a dead zone."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time,
                zone_id="ZONE1",
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
                timestamp=base_time,
                zone_id="ZONE2",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            # Latest event is 35 minutes after ZONE1
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_003",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time + timedelta(minutes=35),
                zone_id="ZONE2",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events)
        
        dead_zones = [a for a in detector.anomalies if a.anomaly_type == "DEAD_ZONE"]
        assert len(dead_zones) > 0
    
    def test_no_dead_zone_with_recent_visit(self):
        """Test no dead zone when recently visited."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ZONE_ENTER,
                timestamp=base_time,
                zone_id="ZONE1",
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
                timestamp=base_time + timedelta(minutes=10),  # Within 30 min
                zone_id="ZONE1",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events)
        
        dead_zones = [a for a in detector.anomalies if a.anomaly_type == "DEAD_ZONE"]
        assert len(dead_zones) == 0


class TestAnomaloySeverity:
    """Test severity level assignment."""
    
    def test_severity_levels(self):
        """Test different severity levels."""
        detector = AnomalyDetector()
        
        # Create anomalies with different severities
        detector.anomalies = [
            Anomaly(
                anomaly_type="DEAD_ZONE",
                severity=AnomalySeverity.INFO,
                description="Zone has no visits",
                metric_value=0,
                threshold=1,
                suggested_action="Check zone"
            ),
            Anomaly(
                anomaly_type="QUEUE_SPIKE",
                severity=AnomalySeverity.WARNING,
                description="Queue spiking",
                metric_value=15,
                threshold=10,
                suggested_action="Open new checkout"
            ),
            Anomaly(
                anomaly_type="CONVERSION_DROP",
                severity=AnomalySeverity.CRITICAL,
                description="Conversion critical",
                metric_value=0.05,
                threshold=0.2,
                suggested_action="Investigate immediately"
            ),
        ]
        
        info_anomalies = detector.get_anomalies_by_severity(AnomalySeverity.INFO)
        warning_anomalies = detector.get_anomalies_by_severity(AnomalySeverity.WARNING)
        critical_anomalies = detector.get_anomalies_by_severity(AnomalySeverity.CRITICAL)
        
        assert len(info_anomalies) == 1
        assert len(warning_anomalies) == 1
        assert len(critical_anomalies) == 1


class TestAnomalyStatistics:
    """Test anomaly statistics."""
    
    def test_get_stats(self):
        """Test getting anomaly statistics."""
        detector = AnomalyDetector()
        
        detector.anomalies = [
            Anomaly(
                anomaly_type="INFO_TEST",
                severity=AnomalySeverity.INFO,
                description="Info anomaly",
                metric_value=1,
                threshold=2,
                suggested_action="Monitor"
            ),
            Anomaly(
                anomaly_type="WARNING_TEST",
                severity=AnomalySeverity.WARNING,
                description="Warning anomaly",
                metric_value=1,
                threshold=2,
                suggested_action="Act"
            ),
        ]
        
        stats = detector.get_stats()
        
        assert stats['total_anomalies'] == 2
        assert stats['info'] == 1
        assert stats['warning'] == 1
        assert stats['critical'] == 0
        assert len(stats['anomalies']) == 2


class TestAnomalyDetectorStaffExclusion:
    """Test staff exclusion."""
    
    def test_staff_excluded_from_detection(self):
        """Test that staff events are excluded."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_STAFF",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=True,  # Staff
                confidence=0.95,
                metadata=EventMetadata(queue_depth=100)
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events)
        
        # Staff events should be ignored
        queue_spikes = [a for a in detector.anomalies if a.anomaly_type == "QUEUE_SPIKE"]
        assert len(queue_spikes) == 0


class TestAnomalyDetectorEdgeCases:
    """Test edge cases."""
    
    def test_no_events(self):
        """Test with no events."""
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies([])
        
        # Should not crash, may or may not have anomalies
        assert isinstance(anomalies, list)
    
    def test_no_anomalies_detected(self):
        """Test normal operation with no anomalies."""
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
                metadata=EventMetadata(queue_depth=3)
            ),
        ]
        
        detector = AnomalyDetector()
        detector.detect_anomalies(events, historical_queue_average=5.0)
        
        # Normal situation, no anomalies
        assert len(detector.anomalies) == 0
    
    def test_get_stats_empty(self):
        """Test stats with no anomalies."""
        detector = AnomalyDetector()
        stats = detector.get_stats()
        
        assert stats['total_anomalies'] == 0
        assert stats['critical'] == 0
        assert stats['warning'] == 0
        assert stats['info'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
