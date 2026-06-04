"""
Metrics Engine Module.

Computes store analytics metrics from events and conversions.

Excludes:
- Staff visitors (is_staff = true)

Handles:
- Zero visitors
- Zero purchases
- Empty stores
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType
from analytics.conversion_engine import ConversionEngine


class MetricsEngine:
    """
    Metrics Engine.
    
    Computes comprehensive store metrics from events and conversions.
    
    Metrics computed:
    - unique_visitors: Count of unique visitors (excl. staff)
    - conversion_rate: Conversions / sessions
    - average_dwell_time: Mean time in store
    - average_dwell_by_zone: Mean time per zone
    - queue_depth: Peak billing queue size
    - abandonment_rate: Queue abandon / queue join
    - revenue: Total conversion revenue
    - average_basket_size: Mean transaction value
    """
    
    def __init__(self):
        """Initialize metrics engine."""
        self.events: List[Event] = []
        self.conversion_engine: Optional[ConversionEngine] = None
        logger.info("MetricsEngine initialized")
    
    def compute_metrics(
        self,
        events: List[Event],
        conversion_engine: ConversionEngine
    ) -> Dict[str, Any]:
        """
        Compute all metrics.
        
        Args:
            events: List of events
            conversion_engine: ConversionEngine with matches
            
        Returns:
            Dict of computed metrics
        """
        self.events = [e for e in events if not e.is_staff]  # Exclude staff
        self.conversion_engine = conversion_engine
        
        return {
            'unique_visitors': self.compute_unique_visitors(),
            'conversion_rate': self.compute_conversion_rate(),
            'average_dwell_time': self.compute_average_dwell_time(),
            'average_dwell_by_zone': self.compute_average_dwell_by_zone(),
            'queue_depth': self.compute_queue_depth(),
            'abandonment_rate': self.compute_abandonment_rate(),
            'revenue': self.compute_revenue(),
            'average_basket_size': self.compute_average_basket_size(),
            'store_footfall': self.compute_footfall(),
            'zone_visit_frequency': self.compute_zone_visit_frequency()
        }
    
    def compute_unique_visitors(self) -> int:
        """
        Compute unique visitor count.

        Primary: distinct visitor_id on ENTRY events.
        Fallback: distinct visitors on entry-role cameras when ENTRY rows are missing
        (e.g. pipeline run before entry events were persisted).
        """
        entry_visitors = set()
        for event in self.events:
            if event.event_type == EventType.ENTRY:
                entry_visitors.add(event.visitor_id)

        if entry_visitors:
            return len(entry_visitors)

        entry_cameras = self._infer_entry_camera_ids()
        if not entry_cameras:
            return len({e.visitor_id for e in self.events})

        return len(
            {
                e.visitor_id
                for e in self.events
                if e.camera_id in entry_cameras
            }
        )

    def _infer_entry_camera_ids(self) -> set[str]:
        """Cameras that look like entry feeds from event patterns."""
        by_camera: dict[str, set[str]] = {}
        for event in self.events:
            by_camera.setdefault(event.camera_id, set()).add(
                (event.zone_id or "").upper()
            )
        entry_cams: set[str] = set()
        for cam_id, zones in by_camera.items():
            if "ENTRY" in zones or cam_id.upper().find("ENTRY") >= 0:
                entry_cams.add(cam_id)
        return entry_cams
    
    def compute_conversion_rate(self) -> float:
        """
        Compute conversion rate.
        
        Returns:
            Conversion rate (0-1)
        """
        if not self.conversion_engine:
            return 0.0
        
        total_entries = len(set(
            e.visitor_id for e in self.events
            if e.event_type == EventType.ENTRY
        ))
        
        if total_entries == 0:
            return 0.0
        
        conversions = self.conversion_engine.compute_purchase_count()
        return conversions / total_entries
    
    def compute_average_dwell_time(self) -> int:
        """
        Compute average dwell time in store.
        
        Uses EXIT event dwell_ms field.
        
        Returns:
            Average dwell time in seconds
        """
        dwell_times = []
        for event in self.events:
            if event.event_type == EventType.EXIT and event.dwell_ms > 0:
                dwell_times.append(event.dwell_ms / 1000)  # Convert to seconds
        
        if not dwell_times:
            return 0
        
        return int(sum(dwell_times) / len(dwell_times))
    
    def compute_average_dwell_by_zone(self) -> Dict[str, int]:
        """
        Compute average dwell time per zone.
        
        Uses ZONE_EXIT event dwell_ms field.
        
        Returns:
            Dict of zone_id -> average dwell in seconds
        """
        zone_dwells: Dict[str, List[int]] = {}
        
        for event in self.events:
            if event.event_type == EventType.ZONE_EXIT and event.zone_id and event.dwell_ms > 0:
                if event.zone_id not in zone_dwells:
                    zone_dwells[event.zone_id] = []
                zone_dwells[event.zone_id].append(event.dwell_ms / 1000)
        
        # Compute averages
        result = {}
        for zone_id, dwells in zone_dwells.items():
            result[zone_id] = int(sum(dwells) / len(dwells)) if dwells else 0
        
        return result
    
    def compute_queue_depth(self) -> int:
        """
        Compute peak queue depth.
        
        Uses max queue_depth from BILLING_QUEUE_JOIN events.
        
        Returns:
            Peak queue depth
        """
        max_depth = 0
        for event in self.events:
            if (event.event_type == EventType.BILLING_QUEUE_JOIN and
                event.metadata and event.metadata.queue_depth):
                max_depth = max(max_depth, event.metadata.queue_depth)
        
        return max_depth
    
    def compute_abandonment_rate(self) -> float:
        """
        Compute queue abandonment rate.
        
        Returns:
            Abandonment rate (0-1) = abandons / joins
        """
        joins = len([
            e for e in self.events
            if e.event_type == EventType.BILLING_QUEUE_JOIN
        ])
        
        abandons = len([
            e for e in self.events
            if e.event_type == EventType.BILLING_QUEUE_ABANDON
        ])
        
        if joins == 0:
            return 0.0
        
        return abandons / joins
    
    def compute_revenue(self) -> float:
        """
        Compute total revenue from conversions.
        
        Returns:
            Total revenue in INR
        """
        if not self.conversion_engine:
            return 0.0
        
        return self.conversion_engine.compute_revenue()
    
    def compute_average_basket_size(self) -> float:
        """
        Compute average basket size.
        
        Returns:
            Average basket value in INR
        """
        if not self.conversion_engine:
            return 0.0
        
        conversions = self.conversion_engine.compute_purchase_count()
        if conversions == 0:
            return 0.0
        
        return self.compute_revenue() / conversions
    
    def compute_footfall(self) -> int:
        """
        Compute total footfall (ENTRY count).
        
        Returns:
            Total number of store entries
        """
        return len([
            e for e in self.events
            if e.event_type == EventType.ENTRY
        ])
    
    def compute_zone_visit_frequency(self) -> Dict[str, int]:
        """
        Compute visit frequency per zone.
        
        Uses ZONE_ENTER events.
        
        Returns:
            Dict of zone_id -> visit count
        """
        zone_visits: Dict[str, int] = {}
        
        for event in self.events:
            if event.event_type == EventType.ZONE_ENTER and event.zone_id:
                zone_visits[event.zone_id] = zone_visits.get(event.zone_id, 0) + 1
        
        return zone_visits
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics state."""
        return {
            'events_processed': len(self.events),
            'conversions': (
                self.conversion_engine.compute_purchase_count()
                if self.conversion_engine else 0
            ),
            'metrics': self.compute_metrics(
                self.events,
                self.conversion_engine or ConversionEngine()
            )
        }


def create_metrics_engine() -> MetricsEngine:
    """
    Factory function to create MetricsEngine.
    
    Returns:
        Configured MetricsEngine
    """
    return MetricsEngine()
