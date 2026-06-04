"""
Heatmap Engine Module.

Generates zone-level heatmap data showing visit frequency and dwell time.

Data Confidence:
- LOW: < 20 sessions
- HIGH: >= 20 sessions
"""

import logging
from typing import List, Dict, Any, Optional
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType


class HeatmapZone:
    """Zone heatmap data."""
    
    def __init__(self, zone_id: str):
        """Initialize zone."""
        self.zone_id = zone_id
        self.visit_count = 0
        self.total_dwell_ms = 0
        self.visit_sessions = []
    
    def add_visit(self, dwell_ms: int):
        """Record a visit."""
        self.visit_count += 1
        self.total_dwell_ms += dwell_ms
        self.visit_sessions.append(dwell_ms)
    
    def get_avg_dwell(self) -> int:
        """Get average dwell time in seconds."""
        if self.visit_count == 0:
            return 0
        return int(self.total_dwell_ms / self.visit_count / 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'zone_id': self.zone_id,
            'visit_frequency': self.visit_count,
            'avg_dwell_seconds': self.get_avg_dwell(),
            'total_dwell_seconds': int(self.total_dwell_ms / 1000)
        }


class HeatmapEngine:
    """
    Heatmap Engine.
    
    Generates zone-level heatmaps with visit frequency,
    dwell time, and normalized heat scores.
    
    Attributes:
        DATA_CONFIDENCE_THRESHOLD: Sessions required for HIGH confidence (default 20)
    """
    
    DATA_CONFIDENCE_THRESHOLD = 20
    
    def __init__(self):
        """Initialize heatmap engine."""
        self.zones: Dict[str, HeatmapZone] = {}
        logger.info(f"HeatmapEngine initialized (threshold={self.DATA_CONFIDENCE_THRESHOLD})")
    
    def compute_heatmap(self, events: List[Event]) -> Dict[str, Any]:
        """
        Compute heatmap data.
        
        Args:
            events: List of events
            
        Returns:
            Heatmap data with zone scores and confidence
        """
        # Exclude staff
        events = [e for e in events if not e.is_staff]
        
        # Reset zones
        self.zones = {}
        
        # Process ZONE_EXIT events (contain dwell_ms)
        for event in events:
            if event.event_type == EventType.ZONE_EXIT and event.zone_id:
                if event.zone_id not in self.zones:
                    self.zones[event.zone_id] = HeatmapZone(event.zone_id)
                self.zones[event.zone_id].add_visit(event.dwell_ms)
        
        # Also process ZONE_DWELL events for additional dwell data
        for event in events:
            if event.event_type == EventType.ZONE_DWELL and event.zone_id:
                if event.zone_id not in self.zones:
                    self.zones[event.zone_id] = HeatmapZone(event.zone_id)
                # Only add if not already counted (avoid double-counting)
                if event.dwell_ms not in self.zones[event.zone_id].visit_sessions:
                    self.zones[event.zone_id].add_visit(event.dwell_ms)
        
        # Normalize and compute heat scores
        heatmap_data = self._normalize_heatmap()
        
        return heatmap_data
    
    def _normalize_heatmap(self) -> Dict[str, Any]:
        """
        Normalize heatmap scores to 0-100 range.
        
        Returns:
            Normalized heatmap data
        """
        if not self.zones:
            return {
                'zones': [],
                'data_confidence': 'LOW',
                'total_sessions': 0
            }
        
        # Find max visit frequency for normalization
        max_visits = max((z.visit_count for z in self.zones.values()), default=1)
        
        # Build result
        zone_data = []
        for zone_id, zone in self.zones.items():
            # Normalize visit frequency to 0-100
            normalized_score = (zone.visit_count / max_visits) * 100 if max_visits > 0 else 0
            
            zone_data.append({
                'zone_id': zone_id,
                'visit_frequency': zone.visit_count,
                'avg_dwell_seconds': zone.get_avg_dwell(),
                'normalized_heat_score': round(normalized_score, 2),
                'total_dwell_seconds': int(zone.total_dwell_ms / 1000)
            })
        
        # Determine confidence based on total sessions
        total_sessions = sum(z.visit_count for z in self.zones.values())
        data_confidence = (
            'HIGH' if total_sessions >= self.DATA_CONFIDENCE_THRESHOLD
            else 'LOW'
        )
        
        return {
            'zones': sorted(zone_data, key=lambda x: x['normalized_heat_score'], reverse=True),
            'data_confidence': data_confidence,
            'total_sessions': total_sessions,
            'zone_count': len(self.zones)
        }
    
    def get_hottest_zones(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get top N hottest zones.
        
        Args:
            top_n: Number of zones to return
            
        Returns:
            Top zones by heat score
        """
        heatmap = self._normalize_heatmap()
        return heatmap['zones'][:top_n]
    
    def get_coldest_zones(self, bottom_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get bottom N coldest zones.
        
        Args:
            bottom_n: Number of zones to return
            
        Returns:
            Bottom zones by heat score
        """
        heatmap = self._normalize_heatmap()
        return heatmap['zones'][-bottom_n:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get heatmap statistics."""
        heatmap = self._normalize_heatmap()
        return {
            'total_zones': len(self.zones),
            'total_visits': sum(z.visit_count for z in self.zones.values()),
            'data_confidence': heatmap['data_confidence'],
            'zones': heatmap['zones']
        }


def create_heatmap_engine() -> HeatmapEngine:
    """
    Factory function to create HeatmapEngine.
    
    Returns:
        Configured HeatmapEngine
    """
    return HeatmapEngine()
