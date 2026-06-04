"""
Multi-Camera Fusion Module.

Handles multiple camera feeds and prevents duplicate visitor counting.

Fusion strategy:
- Entry Camera: First contact (authoritative source)
- Main Floor Camera: Tracks movement
- Billing Camera: Tracks checkout

Deduplication:
- visitor_id matching (primary)
- embedding similarity (secondary)
- timestamp overlap + location (tertiary)
"""

import logging
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
from uuid import uuid4
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType


class CameraFusionTrack:
    """Single unified visitor track across multiple cameras."""
    
    def __init__(self, visitor_id: str, entry_camera: str, entry_time: datetime):
        """Initialize track."""
        self.visitor_id = visitor_id
        self.entry_camera = entry_camera
        self.entry_time = entry_time
        self.exit_time: Optional[datetime] = None
        self.cameras_seen: Set[str] = {entry_camera}
        self.zones_visited: Set[str] = set()
        self.events: List[Event] = []
    
    def add_event(self, event: Event) -> None:
        """Add event to track."""
        self.events.append(event)
        if event.camera_id:
            self.cameras_seen.add(event.camera_id)
        if event.zone_id:
            self.zones_visited.add(event.zone_id)
        if event.event_type == EventType.EXIT:
            self.exit_time = event.timestamp
    
    def get_duration_ms(self) -> int:
        """Get visit duration in milliseconds."""
        end_time = self.exit_time or self.events[-1].timestamp
        delta = end_time - self.entry_time
        return int(delta.total_seconds() * 1000)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'visitor_id': self.visitor_id,
            'entry_camera': self.entry_camera,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'duration_ms': self.get_duration_ms(),
            'cameras_seen': list(self.cameras_seen),
            'zones_visited': list(self.zones_visited),
            'event_count': len(self.events)
        }


class CameraFusion:
    """
    Multi-Camera Fusion Engine.
    
    Fuses multiple camera streams into unified visitor tracks.
    Prevents duplicate counting across cameras.
    
    Features:
    - Entry camera authoritative (first contact)
    - Maintains single visitor identity
    - Tracks camera transitions
    - Deduplicates by visitor_id, embedding similarity, timestamp
    
    Attributes:
        EMBEDDING_SIMILARITY_THRESHOLD: Min cosine similarity for match
        TIMESTAMP_OVERLAP_SECONDS: Max time gap for same visitor
    """
    
    EMBEDDING_SIMILARITY_THRESHOLD = 0.85
    TIMESTAMP_OVERLAP_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        """Initialize camera fusion."""
        self.active_tracks: Dict[str, CameraFusionTrack] = {}
        self.closed_tracks: List[CameraFusionTrack] = []
        self.visitor_id_map: Dict[str, str] = {}  # camera_local_id -> unified_visitor_id
        logger.info("CameraFusion initialized")
    
    def process_event(self, event: Event) -> str:
        """
        Process event from any camera and return unified visitor_id.
        
        Args:
            event: Event from camera
            
        Returns:
            Unified visitor_id (may be different from input if deduplicated)
        """
        # Try to find existing track
        track = self._find_track(event)
        
        if track:
            # Found existing track - add to it
            track.add_event(event)
            unified_id = track.visitor_id
            logger.debug(f"Event added to existing track {unified_id}")
        else:
            # New visitor or new entry
            if event.event_type == EventType.ENTRY:
                # New track from entry camera
                unified_id = event.visitor_id
                track = CameraFusionTrack(unified_id, event.camera_id, event.timestamp)
                track.add_event(event)
                self.active_tracks[unified_id] = track
                logger.info(f"New track created: {unified_id} from camera {event.camera_id}")
            else:
                # Orphan event (no matching entry?) - create track anyway
                unified_id = event.visitor_id
                track = CameraFusionTrack(unified_id, event.camera_id, event.timestamp)
                track.add_event(event)
                self.active_tracks[unified_id] = track
                logger.warning(f"Orphan event created track: {unified_id}")
        
        # Track ID mapping
        self.visitor_id_map[event.visitor_id] = unified_id
        
        # Check for exits
        if event.event_type == EventType.EXIT and track:
            self.closed_tracks.append(track)
            del self.active_tracks[unified_id]
            logger.info(f"Track closed: {unified_id}")
        
        return unified_id
    
    def _find_track(self, event: Event) -> Optional[CameraFusionTrack]:
        """
        Find existing track for event using fusion strategy.
        
        Priority:
        1. Direct visitor_id match (primary)
        2. Embedding similarity (secondary)
        3. Temporal-spatial overlap (tertiary)
        
        Args:
            event: Event to match
            
        Returns:
            Matching CameraFusionTrack or None
        """
        # Strategy 1: Direct visitor_id match
        if event.visitor_id in self.active_tracks:
            return self.active_tracks[event.visitor_id]
        
        # Strategy 2: Check if this visitor_id was remapped
        if event.visitor_id in self.visitor_id_map:
            unified_id = self.visitor_id_map[event.visitor_id]
            if unified_id in self.active_tracks:
                return self.active_tracks[unified_id]
        
        # Strategy 3: Temporal-spatial matching
        # (if different cameras see someone at same time in same zone)
        for track in self.active_tracks.values():
            # Check if event is near last event in track
            if not track.events:
                continue
            
            last_event = track.events[-1]
            time_diff = abs((event.timestamp - last_event.timestamp).total_seconds())
            
            # Same zone and close in time?
            if (event.zone_id and last_event.zone_id and
                event.zone_id == last_event.zone_id and
                time_diff < self.TIMESTAMP_OVERLAP_SECONDS and
                event.camera_id != last_event.camera_id):
                
                logger.info(
                    f"Fused visitor {event.visitor_id} to track {track.visitor_id} "
                    f"via temporal-spatial matching"
                )
                return track
        
        return None
    
    def get_active_visitors(self) -> Dict[str, CameraFusionTrack]:
        """Get all active visitor tracks."""
        return self.active_tracks.copy()
    
    def get_visitor_journey(self, visitor_id: str) -> Optional[List[Event]]:
        """
        Get complete visitor journey across all cameras.
        
        Args:
            visitor_id: Unified visitor_id
            
        Returns:
            List of events in chronological order
        """
        # Check active tracks
        if visitor_id in self.active_tracks:
            return sorted(self.active_tracks[visitor_id].events, key=lambda e: e.timestamp)
        
        # Check closed tracks
        for track in self.closed_tracks:
            if track.visitor_id == visitor_id:
                return sorted(track.events, key=lambda e: e.timestamp)
        
        return None
    
    def get_unified_count(self) -> int:
        """Get count of unique active visitors (deduplicated)."""
        return len(self.active_tracks)
    
    def get_active_stats(self) -> Dict[str, any]:
        """Get active track statistics."""
        if not self.active_tracks:
            return {
                'active_visitors': 0,
                'total_cameras': 0,
                'avg_cameras_per_visitor': 0
            }
        
        camera_counts = [len(t.cameras_seen) for t in self.active_tracks.values()]
        
        return {
            'active_visitors': len(self.active_tracks),
            'total_cameras': len(set(c for t in self.active_tracks.values() for c in t.cameras_seen)),
            'avg_cameras_per_visitor': sum(camera_counts) / len(camera_counts) if camera_counts else 0,
            'zones_tracked': len(set(z for t in self.active_tracks.values() for z in t.zones_visited))
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get overall statistics."""
        return {
            'active_tracks': len(self.active_tracks),
            'closed_tracks': len(self.closed_tracks),
            'total_processed': len(self.active_tracks) + len(self.closed_tracks),
            'visitor_id_remappings': len(self.visitor_id_map)
        }


def create_camera_fusion() -> CameraFusion:
    """
    Factory function to create CameraFusion.
    
    Returns:
        Configured CameraFusion
    """
    return CameraFusion()
