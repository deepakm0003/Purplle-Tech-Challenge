"""
Visitor State Management Module

Tracks visitor sessions and state across video frames.
Maintains thread-safe visitor state with zone assignments and dwell times.
"""

import logging
import threading
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


@dataclass
class VisitorSession:
    """
    Represents a visitor session during store visit.
    
    Attributes:
        visitor_id: Unique visitor identifier
        session_id: Unique session identifier
        track_id: Current track ID
        first_seen_frame: Frame number when first detected
        last_seen_frame: Frame number of last detection
        zones_visited: Set of zone IDs visited
        zone_entry_frames: Dict of zone_id -> entry frame number
        dwell_times: Dict of zone_id -> total dwell frames
        current_zone: Current zone ID (None if not in zone)
        entry_count: Number of entries into store
        active: Whether session is still active
    """
    
    visitor_id: str
    session_id: str
    track_id: int
    first_seen_frame: int
    last_seen_frame: int
    zones_visited: Set[int] = field(default_factory=set)
    zone_entry_frames: Dict[int, int] = field(default_factory=dict)
    dwell_times: Dict[int, int] = field(default_factory=dict)
    current_zone: Optional[int] = None
    entry_count: int = 1
    active: bool = True
    
    def get_dwell_time(self, zone_id: int) -> int:
        """Get total dwell time for a zone (in frames)."""
        return self.dwell_times.get(zone_id, 0)
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary."""
        return {
            "visitor_id": self.visitor_id,
            "session_id": self.session_id,
            "track_id": self.track_id,
            "first_seen_frame": self.first_seen_frame,
            "last_seen_frame": self.last_seen_frame,
            "zones_visited": list(self.zones_visited),
            "dwell_times": dict(self.dwell_times),
            "current_zone": self.current_zone,
            "entry_count": self.entry_count,
            "active": self.active,
            "duration_frames": self.last_seen_frame - self.first_seen_frame
        }


class VisitorStateManager:
    """
    Thread-safe Visitor State Manager.
    
    Maintains visitor sessions, tracks zone assignments, and dwell times.
    Handles session creation, updates, and cleanup.
    
    Attributes:
        sessions: Dict of track_id -> VisitorSession
        track_to_visitor: Dict of track_id -> visitor_id
        visitor_sessions: Dict of visitor_id -> List[VisitorSession]
        session_timeout: Frames before session is marked inactive
        lock: Thread lock for thread safety
    """
    
    def __init__(self, session_timeout: int = 300):
        """
        Initialize VisitorStateManager.
        
        Args:
            session_timeout: Frames before marking session inactive
        """
        self.sessions: Dict[int, VisitorSession] = {}
        self.track_to_visitor: Dict[int, str] = {}
        self.visitor_sessions: Dict[str, List[VisitorSession]] = {}
        self.session_timeout = session_timeout
        self.lock = threading.RLock()
        self.frame_count = 0
        
        logger.info(
            f"VisitorStateManager init: session_timeout={session_timeout}"
        )
    
    def create_session(
        self,
        track_id: int,
        current_frame: int,
        visitor_id: Optional[str] = None
    ) -> VisitorSession:
        """
        Create a new visitor session.
        
        Args:
            track_id: Track ID for this session
            current_frame: Current frame number
            visitor_id: Optional visitor ID (generated if not provided)
            
        Returns:
            Created VisitorSession
        """
        with self.lock:
            if visitor_id is None:
                visitor_id = str(uuid.uuid4())
            
            session_id = str(uuid.uuid4())
            
            session = VisitorSession(
                visitor_id=visitor_id,
                session_id=session_id,
                track_id=track_id,
                first_seen_frame=current_frame,
                last_seen_frame=current_frame
            )
            
            self.sessions[track_id] = session
            self.track_to_visitor[track_id] = visitor_id
            
            if visitor_id not in self.visitor_sessions:
                self.visitor_sessions[visitor_id] = []
            self.visitor_sessions[visitor_id].append(session)
            
            logger.debug(
                f"Created session: track_id={track_id}, visitor_id={visitor_id}, "
                f"session_id={session_id}"
            )
            
            return session
    
    def update_session(
        self,
        track_id: int,
        current_frame: int,
        zone_id: Optional[int] = None
    ) -> Optional[VisitorSession]:
        """
        Update an existing session.
        
        Args:
            track_id: Track ID to update
            current_frame: Current frame number
            zone_id: Current zone ID (None if not in zone)
            
        Returns:
            Updated session or None if not found
        """
        with self.lock:
            session = self.sessions.get(track_id)
            if session is None:
                return None
            
            session.last_seen_frame = current_frame
            session.active = True
            
            # Update zone information
            if zone_id is not None:
                session.zones_visited.add(zone_id)
                
                # Track zone entry
                if session.current_zone != zone_id:
                    # Exiting previous zone
                    if session.current_zone is not None:
                        prev_zone = session.current_zone
                        dwell_frames = current_frame - session.zone_entry_frames.get(prev_zone, current_frame)
                        session.dwell_times[prev_zone] = session.dwell_times.get(prev_zone, 0) + dwell_frames
                    
                    # Entering new zone
                    session.current_zone = zone_id
                    session.zone_entry_frames[zone_id] = current_frame
                else:
                    # Still in same zone - increment dwell
                    pass
            
            return session
    
    def end_session(self, track_id: int, current_frame: int) -> Optional[VisitorSession]:
        """
        Mark a session as inactive.
        
        Args:
            track_id: Track ID to end
            current_frame: Current frame number
            
        Returns:
            Ended session or None if not found
        """
        with self.lock:
            session = self.sessions.get(track_id)
            if session is None:
                return None
            
            session.last_seen_frame = current_frame
            session.active = False
            
            # Add final dwell time if in a zone
            if session.current_zone is not None:
                zone_id = session.current_zone
                dwell_frames = current_frame - session.zone_entry_frames.get(zone_id, current_frame)
                session.dwell_times[zone_id] = session.dwell_times.get(zone_id, 0) + dwell_frames
            
            logger.debug(
                f"Ended session: track_id={track_id}, visitor_id={session.visitor_id}, "
                f"duration_frames={current_frame - session.first_seen_frame}"
            )
            
            return session
    
    def get_session(self, track_id: int) -> Optional[VisitorSession]:
        """Get a session by track ID."""
        with self.lock:
            return self.sessions.get(track_id)
    
    def get_visitor_sessions(self, visitor_id: str) -> List[VisitorSession]:
        """Get all sessions for a visitor."""
        with self.lock:
            return self.visitor_sessions.get(visitor_id, [])
    
    def get_active_sessions(self) -> List[VisitorSession]:
        """Get all active sessions."""
        with self.lock:
            return [s for s in self.sessions.values() if s.active]
    
    def get_inactive_sessions(self) -> List[VisitorSession]:
        """Get all inactive sessions."""
        with self.lock:
            return [s for s in self.sessions.values() if not s.active]
    
    def cleanup_aged_sessions(self, current_frame: int) -> int:
        """
        Mark sessions as inactive if no updates for timeout period.
        
        Args:
            current_frame: Current frame number
            
        Returns:
            Number of sessions cleaned up
        """
        with self.lock:
            cleaned_count = 0
            
            for track_id, session in list(self.sessions.items()):
                if session.active and (current_frame - session.last_seen_frame) > self.session_timeout:
                    session.active = False
                    cleaned_count += 1
                    
                    logger.debug(
                        f"Aged out session: track_id={track_id}, visitor_id={session.visitor_id}, "
                        f"frames_since_update={current_frame - session.last_seen_frame}"
                    )
            
            return cleaned_count
    
    def update_frame_count(self, frame_num: int) -> None:
        """Update current frame count."""
        with self.lock:
            self.frame_count = frame_num
    
    def get_stats(self) -> Dict:
        """Get manager statistics."""
        with self.lock:
            active = [s for s in self.sessions.values() if s.active]
            inactive = [s for s in self.sessions.values() if not s.active]
            
            return {
                "frame_count": self.frame_count,
                "total_sessions": len(self.sessions),
                "active_sessions": len(active),
                "inactive_sessions": len(inactive),
                "total_unique_visitors": len(self.visitor_sessions),
                "session_timeout": self.session_timeout
            }
    
    def reset(self) -> None:
        """Reset manager state."""
        with self.lock:
            self.sessions.clear()
            self.track_to_visitor.clear()
            self.visitor_sessions.clear()
            self.frame_count = 0
            logger.info("VisitorStateManager reset")


def create_visitor_manager(session_timeout: int = 300) -> VisitorStateManager:
    """
    Factory function to create VisitorStateManager.
    
    Args:
        session_timeout: Frames before marking session inactive
        
    Returns:
        Configured VisitorStateManager instance
    """
    return VisitorStateManager(session_timeout=session_timeout)
