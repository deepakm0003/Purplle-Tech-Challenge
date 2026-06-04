"""
Funnel Engine Module.

Tracks visitor journey through store funnel:
Entry → Zone Visit → Billing Queue → Purchase

Requirements:
- Session-based tracking
- No double-counting
- Re-entries don't create duplicate sessions
"""

import logging
from typing import List, Dict, Any, Optional, Set
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType
from analytics.conversion_engine import ConversionEngine


class FunnelStage:
    """Single stage in the funnel."""
    
    def __init__(self, stage_name: str, count: int = 0):
        """Initialize stage."""
        self.stage_name = stage_name
        self.count = count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'stage': self.stage_name,
            'count': self.count
        }


class FunnelEngine:
    """
    Funnel Engine.
    
    Tracks visitor progression through store funnel.
    
    Stages:
    1. Entry - Visitor entered store (ENTRY event)
    2. Zone - Visitor visited any zone (ZONE_ENTER event)
    3. Billing - Visitor joined billing queue (BILLING_QUEUE_JOIN event)
    4. Purchase - Visitor completed purchase (conversion matched)
    
    Features:
    - Session-based (no double-counting per visitor)
    - Re-entries tracked separately
    """
    
    def __init__(self):
        """Initialize funnel engine."""
        self.stages = {
            'entry': set(),
            'zone': set(),
            'billing': set(),
            'purchase': set()
        }
        logger.info("FunnelEngine initialized")
    
    def compute_funnel(
        self,
        events: List[Event],
        conversion_engine: ConversionEngine
    ) -> Dict[str, Any]:
        """
        Compute funnel progression.
        
        Args:
            events: List of events
            conversion_engine: Engine with conversion matches
            
        Returns:
            Funnel metrics dict
        """
        # Exclude staff
        events = [e for e in events if not e.is_staff]
        
        # Reset stages
        self.stages = {
            'entry': set(),
            'zone': set(),
            'billing': set(),
            'purchase': set()
        }
        
        # Stage 1: Entry
        # Count unique visitors who entered (first entry per visitor)
        for event in events:
            if event.event_type == EventType.ENTRY:
                self.stages['entry'].add(event.visitor_id)
        
        # Stage 2: Zone Visit
        # Count unique visitors who visited any zone
        for event in events:
            if (event.event_type == EventType.ZONE_ENTER and
                event.visitor_id in self.stages['entry']):
                self.stages['zone'].add(event.visitor_id)
        
        # Stage 3: Billing Queue
        # Count unique visitors who joined billing queue
        for event in events:
            if (event.event_type == EventType.BILLING_QUEUE_JOIN and
                event.visitor_id in self.stages['entry']):
                self.stages['billing'].add(event.visitor_id)
        
        # Stage 4: Purchase
        # Count unique visitors who made a purchase
        for conversion in conversion_engine.get_conversions():
            self.stages['purchase'].add(conversion.visitor_id)
        
        # Compute dropoff percentages
        entry_count = len(self.stages['entry'])
        
        return {
            'entry_count': entry_count,
            'zone_count': len(self.stages['zone']),
            'billing_count': len(self.stages['billing']),
            'purchase_count': len(self.stages['purchase']),
            'dropoff_percentages': {
                'entry_to_zone': self._calculate_dropoff(
                    self.stages['entry'], self.stages['zone']
                ),
                'zone_to_billing': self._calculate_dropoff(
                    self.stages['zone'], self.stages['billing']
                ),
                'billing_to_purchase': self._calculate_dropoff(
                    self.stages['billing'], self.stages['purchase']
                ),
                'overall_conversion': self._calculate_dropoff(
                    self.stages['entry'], self.stages['purchase']
                )
            }
        }
    
    def _calculate_dropoff(self, from_set: Set[str], to_set: Set[str]) -> float:
        """
        Calculate dropoff percentage between stages.
        
        Args:
            from_set: Starting stage set
            to_set: Ending stage set
            
        Returns:
            Dropoff percentage (0-100)
        """
        if len(from_set) == 0:
            return 0.0
        
        progression = len(from_set & to_set)  # Intersection
        return ((len(from_set) - progression) / len(from_set)) * 100
    
    def get_funnel_efficiency(self) -> float:
        """
        Get overall funnel efficiency.
        
        Returns:
            Efficiency as percentage (0-100)
        """
        if len(self.stages['entry']) == 0:
            return 0.0
        
        conversion_rate = len(self.stages['purchase']) / len(self.stages['entry'])
        return conversion_rate * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get funnel statistics."""
        return {
            'total_entry': len(self.stages['entry']),
            'total_zone': len(self.stages['zone']),
            'total_billing': len(self.stages['billing']),
            'total_purchase': len(self.stages['purchase']),
            'efficiency_percentage': self.get_funnel_efficiency(),
            'stages': {
                k: len(v) for k, v in self.stages.items()
            }
        }


def create_funnel_engine() -> FunnelEngine:
    """
    Factory function to create FunnelEngine.
    
    Returns:
        Configured FunnelEngine
    """
    return FunnelEngine()
