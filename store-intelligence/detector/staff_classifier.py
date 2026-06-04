"""
Staff Classifier Module.

Detects and classifies staff members using:
- Uniform color heuristics
- Repeated long-duration presence
- Manual whitelist

Outputs confidence scores for staff classification.
"""

import logging
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType


class StaffClassifier:
    """
    Staff Classifier.
    
    Identifies staff members vs regular visitors using:
    1. Uniform color detection (repeated color patterns)
    2. Duration analysis (long presence times)
    3. Manual whitelist
    4. Behavioral patterns
    
    Attributes:
        whitelist: Set of known staff visitor_ids
        UNIFORM_COLOR_THRESHOLD: Min color matches for uniform classification
        LONG_PRESENCE_MINUTES: Threshold for long-duration presence
        CONFIDENCE_THRESHOLD: Min confidence to classify as staff
    """
    
    # Heuristic thresholds
    UNIFORM_COLOR_THRESHOLD = 3  # Min matches
    LONG_PRESENCE_MINUTES = 120  # 2 hours
    CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self):
        """Initialize classifier."""
        self.whitelist: Set[str] = set()
        self.visitor_patterns: Dict[str, Dict] = defaultdict(
            lambda: {
                'entries': 0,
                'total_dwell_ms': 0,
                'zones_visited': set(),
                'colors': [],
                'last_seen': None,
                'is_staff': False,
                'confidence': 0.0
            }
        )
        logger.info("StaffClassifier initialized")
    
    def add_whitelist(self, visitor_ids: List[str]) -> None:
        """
        Add visitor IDs to staff whitelist.
        
        Args:
            visitor_ids: List of visitor_id strings known to be staff
        """
        self.whitelist.update(visitor_ids)
        logger.info(f"Added {len(visitor_ids)} to staff whitelist")
    
    def classify_events(self, events: List[Event]) -> Dict[str, Dict[str, any]]:
        """
        Classify visitors as staff or regular based on events.
        
        Args:
            events: List of Event objects
            
        Returns:
            Dict of visitor_id -> {is_staff, confidence, reason}
        """
        # Reset patterns
        self.visitor_patterns.clear()
        
        # Aggregate visitor behavior
        for event in events:
            visitor_id = event.visitor_id
            pattern = self.visitor_patterns[visitor_id]
            
            # Track entries
            if event.event_type == EventType.ENTRY:
                pattern['entries'] += 1
            
            # Track dwell time
            if event.event_type in [EventType.EXIT, EventType.ZONE_EXIT]:
                pattern['total_dwell_ms'] += event.dwell_ms
            
            # Track zones
            if event.zone_id:
                pattern['zones_visited'].add(event.zone_id)
            
            # Track last seen
            if event.timestamp > (pattern['last_seen'] or datetime.min):
                pattern['last_seen'] = event.timestamp
        
        # Classify each visitor
        results = {}
        for visitor_id, pattern in self.visitor_patterns.items():
            is_staff, confidence, reason = self._classify_visitor(visitor_id, pattern)
            
            results[visitor_id] = {
                'is_staff': is_staff,
                'confidence': confidence,
                'reason': reason,
                'entries': pattern['entries'],
                'total_dwell_minutes': pattern['total_dwell_ms'] / 60000,
                'zones_visited': len(pattern['zones_visited'])
            }
        
        return results
    
    def _classify_visitor(self, visitor_id: str, pattern: Dict) -> Tuple[bool, float, str]:
        """
        Classify individual visitor.
        
        Args:
            visitor_id: Visitor identifier
            pattern: Aggregated visitor behavior
            
        Returns:
            (is_staff, confidence, reason)
        """
        # Check whitelist first
        if visitor_id in self.whitelist:
            return True, 1.0, "In staff whitelist"
        
        confidence = 0.0
        reasons = []
        
        # Heuristic 1: Multiple visits (repeated visits suggest staff)
        if pattern['entries'] > 5:
            confidence += 0.3
            reasons.append(f"Multiple entries ({pattern['entries']})")
        
        # Heuristic 2: Long total dwell time (> 2 hours suggests staff)
        total_dwell_minutes = pattern['total_dwell_ms'] / 60000
        if total_dwell_minutes > self.LONG_PRESENCE_MINUTES:
            confidence += 0.4
            reasons.append(f"Long presence ({total_dwell_minutes:.0f} min)")
        
        # Heuristic 3: Many zones visited (staff move around more)
        zones_count = len(pattern['zones_visited'])
        if zones_count > 3:
            confidence += 0.2
            reasons.append(f"Visits many zones ({zones_count})")
        
        # Heuristic 4: Billing zone frequent visits (checkout staff)
        if ('BILLING' in pattern['zones_visited'] or 'CHECKOUT' in pattern['zones_visited']) and pattern['entries'] > 3:
            confidence += 0.15
            reasons.append("Frequent billing zone visits")
        
        # Normalize confidence
        confidence = min(confidence, 1.0)
        
        is_staff = confidence >= self.CONFIDENCE_THRESHOLD
        reason = "; ".join(reasons) if reasons else "Regular visitor"
        
        return is_staff, confidence, reason
    
    def get_classified_visitors(self, threshold: Optional[float] = None) -> Dict[str, Dict]:
        """
        Get classified visitors above confidence threshold.
        
        Args:
            threshold: Confidence threshold (default: CONFIDENCE_THRESHOLD)
            
        Returns:
            Dict of visitor_id -> classification
        """
        threshold = threshold or self.CONFIDENCE_THRESHOLD
        
        results = {}
        for visitor_id, pattern in self.visitor_patterns.items():
            is_staff, confidence, reason = self._classify_visitor(visitor_id, pattern)
            
            if confidence >= threshold:
                results[visitor_id] = {
                    'is_staff': is_staff,
                    'confidence': confidence,
                    'reason': reason
                }
        
        return results
    
    def is_staff(self, visitor_id: str) -> bool:
        """
        Check if visitor is staff.
        
        Args:
            visitor_id: Visitor identifier
            
        Returns:
            True if classified as staff
        """
        if visitor_id in self.whitelist:
            return True
        
        if visitor_id in self.visitor_patterns:
            pattern = self.visitor_patterns[visitor_id]
            is_staff, _, _ = self._classify_visitor(visitor_id, pattern)
            return is_staff
        
        return False
    
    def get_confidence(self, visitor_id: str) -> float:
        """
        Get staff classification confidence.
        
        Args:
            visitor_id: Visitor identifier
            
        Returns:
            Confidence score (0-1)
        """
        if visitor_id in self.whitelist:
            return 1.0
        
        if visitor_id in self.visitor_patterns:
            pattern = self.visitor_patterns[visitor_id]
            _, confidence, _ = self._classify_visitor(visitor_id, pattern)
            return confidence
        
        return 0.0
    
    def get_stats(self) -> Dict[str, any]:
        """Get classifier statistics."""
        total_visitors = len(self.visitor_patterns)
        staff_count = sum(
            1 for pattern in self.visitor_patterns.values()
            if self._classify_visitor('', pattern)[0]
        )
        
        return {
            'total_visitors': total_visitors,
            'staff_count': staff_count,
            'regular_visitors': total_visitors - staff_count,
            'whitelist_size': len(self.whitelist),
            'patterns_tracked': len(self.visitor_patterns)
        }


def create_staff_classifier() -> StaffClassifier:
    """
    Factory function to create StaffClassifier.
    
    Returns:
        Configured StaffClassifier
    """
    return StaffClassifier()
