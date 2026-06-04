"""
Anomaly Detection Module.

Detects operational anomalies:
1. Queue Spike - Current queue > rolling average
2. Conversion Drop - Current conversion significantly below historical average
3. Dead Zone - No visits in zone for 30 minutes

Severity levels: INFO, WARNING, CRITICAL
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType


class AnomalySeverity(str, Enum):
    """Anomaly severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Anomaly:
    """Detected anomaly."""
    
    def __init__(
        self,
        anomaly_type: str,
        severity: AnomalySeverity,
        description: str,
        metric_value: float,
        threshold: float,
        suggested_action: str
    ):
        """Initialize anomaly."""
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.description = description
        self.metric_value = metric_value
        self.threshold = threshold
        self.suggested_action = suggested_action
        self.detected_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'anomaly_type': self.anomaly_type,
            'severity': self.severity.value,
            'description': self.description,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'suggested_action': self.suggested_action,
            'detected_at': self.detected_at.isoformat()
        }


class AnomalyDetector:
    """
    Anomaly Detector.
    
    Detects operational anomalies:
    1. Queue Spike - Current queue > rolling average
    2. Conversion Drop - Current conversion significantly below historical
    3. Dead Zone - No visits in zone for 30 minutes
    
    Attributes:
        QUEUE_SPIKE_THRESHOLD: Multiplier for queue average (default 1.5x)
        CONVERSION_DROP_THRESHOLD: Percentage drop for alert (default 25%)
        DEAD_ZONE_MINUTES: Minutes without visits (default 30)
    """
    
    QUEUE_SPIKE_THRESHOLD = 1.5
    CONVERSION_DROP_THRESHOLD = 25  # percentage
    DEAD_ZONE_MINUTES = 30
    
    def __init__(self):
        """Initialize anomaly detector."""
        self.anomalies: List[Anomaly] = []
        logger.info("AnomalyDetector initialized")
    
    def detect_anomalies(
        self,
        events: List[Event],
        historical_conversion_rate: Optional[float] = None,
        historical_queue_average: Optional[float] = None
    ) -> List[Anomaly]:
        """
        Detect all active anomalies.
        
        Args:
            events: List of events
            historical_conversion_rate: Historical conversion rate for comparison
            historical_queue_average: Historical queue average for comparison
            
        Returns:
            List of detected anomalies
        """
        # Exclude staff
        events = [e for e in events if not e.is_staff]
        
        self.anomalies = []
        
        # 1. Queue spike detection
        queue_anomalies = self._detect_queue_spike(events, historical_queue_average)
        self.anomalies.extend(queue_anomalies)
        
        # 2. Conversion drop detection
        conversion_anomalies = self._detect_conversion_drop(
            events, historical_conversion_rate
        )
        self.anomalies.extend(conversion_anomalies)
        
        # 3. Dead zone detection
        dead_zone_anomalies = self._detect_dead_zones(events)
        self.anomalies.extend(dead_zone_anomalies)
        
        logger.info(f"Detected {len(self.anomalies)} anomalies")
        return self.anomalies
    
    def _detect_queue_spike(
        self,
        events: List[Event],
        historical_average: Optional[float] = None
    ) -> List[Anomaly]:
        """
        Detect queue spikes.
        
        Args:
            events: List of events
            historical_average: Historical queue average
            
        Returns:
            Queue spike anomalies
        """
        anomalies = []
        
        # Get current queue depths
        queue_depths = []
        for event in events:
            if (event.event_type == EventType.BILLING_QUEUE_JOIN and
                event.metadata and event.metadata.queue_depth):
                queue_depths.append(event.metadata.queue_depth)
        
        if not queue_depths:
            return anomalies
        
        current_max = max(queue_depths)
        current_avg = sum(queue_depths) / len(queue_depths)
        
        # Use historical if provided, else use current
        comparison_avg = historical_average or current_avg
        
        if comparison_avg == 0:
            comparison_avg = 1  # Avoid division by zero
        
        spike_ratio = current_max / comparison_avg
        
        # Check if spike detected
        if spike_ratio > self.QUEUE_SPIKE_THRESHOLD:
            severity = (
                AnomalySeverity.CRITICAL if spike_ratio > 2.0
                else AnomalySeverity.WARNING
            )
            
            anomaly = Anomaly(
                anomaly_type="QUEUE_SPIKE",
                severity=severity,
                description=f"Queue depth {current_max} exceeds threshold ({spike_ratio:.1f}x average)",
                metric_value=current_max,
                threshold=comparison_avg * self.QUEUE_SPIKE_THRESHOLD,
                suggested_action="Open additional checkout counter" if severity == AnomalySeverity.CRITICAL else "Monitor queue"
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_conversion_drop(
        self,
        events: List[Event],
        historical_rate: Optional[float] = None
    ) -> List[Anomaly]:
        """
        Detect conversion rate drops.
        
        Args:
            events: List of events
            historical_rate: Historical conversion rate
            
        Returns:
            Conversion drop anomalies
        """
        anomalies = []
        
        if not historical_rate or historical_rate == 0:
            return anomalies
        
        # Calculate current conversion rate
        entries = len([e for e in events if e.event_type == EventType.ENTRY])
        purchases = len([e for e in events if e.event_type == EventType.ZONE_EXIT and e.zone_id == "BILLING"])
        
        if entries == 0:
            return anomalies
        
        current_rate = purchases / entries
        drop_percentage = ((historical_rate - current_rate) / historical_rate) * 100
        
        # Check if drop detected
        if drop_percentage > self.CONVERSION_DROP_THRESHOLD:
            severity = (
                AnomalySeverity.CRITICAL if drop_percentage > 50
                else AnomalySeverity.WARNING
            )
            
            anomaly = Anomaly(
                anomaly_type="CONVERSION_DROP",
                severity=severity,
                description=f"Conversion rate {current_rate:.1%} is {drop_percentage:.1f}% below historical {historical_rate:.1%}",
                metric_value=current_rate,
                threshold=historical_rate * (1 - self.CONVERSION_DROP_THRESHOLD / 100),
                suggested_action="Review store layout and promotions" if severity == AnomalySeverity.CRITICAL else "Monitor conversion trends"
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_dead_zones(self, events: List[Event]) -> List[Anomaly]:
        """
        Detect zones with no recent visits.
        
        Args:
            events: List of events
            
        Returns:
            Dead zone anomalies
        """
        anomalies = []
        
        if not events:
            return anomalies
        
        # Get latest event timestamp
        latest_time = max(e.timestamp for e in events)
        dead_zone_cutoff = latest_time - timedelta(minutes=self.DEAD_ZONE_MINUTES)
        
        # Find all zones
        all_zones = set()
        recent_zones = set()
        
        for event in events:
            if event.zone_id and event.event_type == EventType.ZONE_ENTER:
                all_zones.add(event.zone_id)
                if event.timestamp > dead_zone_cutoff:
                    recent_zones.add(event.zone_id)
        
        # Find dead zones
        dead_zones = all_zones - recent_zones
        
        for zone_id in dead_zones:
            anomaly = Anomaly(
                anomaly_type="DEAD_ZONE",
                severity=AnomalySeverity.INFO,
                description=f"Zone {zone_id} has no visits in last {self.DEAD_ZONE_MINUTES} minutes",
                metric_value=0,
                threshold=1,
                suggested_action="Check zone signage and lighting"
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def get_anomalies_by_severity(self, severity: AnomalySeverity) -> List[Anomaly]:
        """
        Get anomalies by severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Anomalies matching severity
        """
        return [a for a in self.anomalies if a.severity == severity]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get anomaly statistics."""
        return {
            'total_anomalies': len(self.anomalies),
            'critical': len(self.get_anomalies_by_severity(AnomalySeverity.CRITICAL)),
            'warning': len(self.get_anomalies_by_severity(AnomalySeverity.WARNING)),
            'info': len(self.get_anomalies_by_severity(AnomalySeverity.INFO)),
            'anomalies': [a.to_dict() for a in self.anomalies]
        }


def create_anomaly_detector() -> AnomalyDetector:
    """
    Factory function to create AnomalyDetector.
    
    Returns:
        Configured AnomalyDetector
    """
    return AnomalyDetector()
