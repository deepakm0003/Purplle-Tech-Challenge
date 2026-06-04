"""
Session Management Module.

Maintains visitor sessions with detailed tracking of movements,
zone visits, dwell times, and session lifecycle.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class VisitorSession:
    """
    Complete visitor session record.
    
    Attributes:
        visitor_id: Unique visitor identifier
        track_id: Associated detector track ID
        entry_time: When visitor entered
        exit_time: When visitor left
        zones_visited: List of zones visited
        current_zone: Current zone
        zone_dwell: Dict of zone -> total dwell time
        is_staff: Whether visitor is staff
        is_active: Whether session is active
        reentry: If this is a re-entry
        purchase_amount: If applicable
    """
    
    def __init__(
        self,
        visitor_id: str,
        track_id: int,
        entry_time: datetime = None
    ):
        """Initialize visitor session."""
        self.visitor_id = visitor_id
        self.track_id = track_id
        self.entry_time = entry_time or datetime.utcnow()
        self.exit_time: Optional[datetime] = None
        
        self.zones_visited: List[str] = []
        self.zone_entry_times: Dict[str, datetime] = {}
        self.zone_dwell_times: Dict[str, int] = {}  # zone -> seconds
        
        self.current_zone: Optional[str] = None
        self.is_staff = False
        self.is_active = True
        self.is_reentry = False
        self.reentry_count = 0
        self.purchase_amount: Optional[float] = None
        
        self.dwell_last_event: Dict[str, datetime] = {}  # For ZONE_DWELL events
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        total_dwell = 0
        if self.exit_time:
            total_dwell = int((self.exit_time - self.entry_time).total_seconds())
        else:
            total_dwell = int((datetime.utcnow() - self.entry_time).total_seconds())
        
        return {
            'visitor_id': self.visitor_id,
            'track_id': self.track_id,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'total_dwell_seconds': total_dwell,
            'zones_visited': self.zones_visited,
            'zone_dwell_times': self.zone_dwell_times,
            'current_zone': self.current_zone,
            'is_staff': self.is_staff,
            'is_active': self.is_active,
            'is_reentry': self.is_reentry,
            'reentry_count': self.reentry_count,
            'purchase_amount': self.purchase_amount
        }
    
    def get_total_dwell(self) -> int:
        """Get total time in store (seconds)."""
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds())
        return int((datetime.utcnow() - self.entry_time).total_seconds())
    
    def get_zone_dwell(self, zone_id: str) -> int:
        """Get total dwell time in zone (seconds)."""
        return self.zone_dwell_times.get(zone_id, 0)


class SessionManager:
    """
    Thread-safe manager for visitor sessions.
    
    Maintains active sessions, handles zone transitions,
    tracks dwell times, and generates session lifecycle events.
    
    Attributes:
        active_sessions: Currently active sessions
        completed_sessions: Finished sessions
        session_timeout: Minutes before session auto-closes
    """
    
    def __init__(self, session_timeout_minutes: int = 5):
        """
        Initialize session manager.
        
        Args:
            session_timeout_minutes: Minutes before session expires
        """
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        self.active_sessions: Dict[str, VisitorSession] = {}
        self.completed_sessions: List[VisitorSession] = []
        self.track_to_visitor: Dict[int, str] = {}
        
        self._lock = threading.RLock()
        
        logger.info(f"SessionManager initialized: timeout={session_timeout_minutes}min")
    
    def start_session(
        self,
        track_id: int,
        visitor_id: Optional[str] = None
    ) -> VisitorSession:
        """
        Start a new visitor session.
        
        Args:
            track_id: Associated detector track ID
            visitor_id: Visitor ID (generated if None)
            
        Returns:
            Created VisitorSession
        """
        with self._lock:
            if visitor_id is None:
                visitor_id = f"VIS_{uuid.uuid4().hex[:8]}"
            
            session = VisitorSession(visitor_id, track_id)
            self.active_sessions[visitor_id] = session
            self.track_to_visitor[track_id] = visitor_id
            
            logger.debug(f"Started session: {visitor_id} (track {track_id})")
            return session
    
    def update_session(
        self,
        visitor_id: str,
        current_zone: Optional[str] = None
    ) -> Optional[VisitorSession]:
        """
        Update session with current location.
        
        Args:
            visitor_id: Visitor ID
            current_zone: Current zone (or None if left store)
            
        Returns:
            Updated session or None if not found
        """
        with self._lock:
            if visitor_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[visitor_id]
            session.last_updated = datetime.utcnow()
            
            # Handle zone transition
            if current_zone is not None:
                if current_zone != session.current_zone:
                    # Exiting previous zone
                    if session.current_zone is not None:
                        prev_zone = session.current_zone
                        if prev_zone in session.zone_entry_times:
                            dwell_seconds = int(
                                (datetime.utcnow() - session.zone_entry_times[prev_zone]).total_seconds()
                            )
                            session.zone_dwell_times[prev_zone] = (
                                session.zone_dwell_times.get(prev_zone, 0) + dwell_seconds
                            )
                    
                    # Entering new zone
                    session.current_zone = current_zone
                    session.zone_entry_times[current_zone] = datetime.utcnow()
                    
                    if current_zone not in session.zones_visited:
                        session.zones_visited.append(current_zone)
                    
                    logger.debug(f"Session {visitor_id}: {session.current_zone}")
            else:
                # Left store (no zone)
                if session.current_zone is not None:
                    prev_zone = session.current_zone
                    if prev_zone in session.zone_entry_times:
                        dwell_seconds = int(
                            (datetime.utcnow() - session.zone_entry_times[prev_zone]).total_seconds()
                        )
                        session.zone_dwell_times[prev_zone] = (
                            session.zone_dwell_times.get(prev_zone, 0) + dwell_seconds
                        )
                    session.current_zone = None
            
            return session
    
    def close_session(
        self,
        visitor_id: str
    ) -> Optional[VisitorSession]:
        """
        Close and complete a visitor session.
        
        Args:
            visitor_id: Visitor ID
            
        Returns:
            Completed session or None if not found
        """
        with self._lock:
            if visitor_id not in self.active_sessions:
                return None
            
            session = self.active_sessions.pop(visitor_id)
            session.exit_time = datetime.utcnow()
            session.is_active = False
            
            # Final zone dwell calculation
            if session.current_zone is not None:
                zone = session.current_zone
                if zone in session.zone_entry_times:
                    dwell_seconds = int(
                        (session.exit_time - session.zone_entry_times[zone]).total_seconds()
                    )
                    session.zone_dwell_times[zone] = (
                        session.zone_dwell_times.get(zone, 0) + dwell_seconds
                    )
                session.current_zone = None
            
            self.completed_sessions.append(session)
            
            # Clean up mapping
            track_id = session.track_id
            if track_id in self.track_to_visitor:
                del self.track_to_visitor[track_id]
            
            logger.info(f"Closed session: {visitor_id}, dwell: {session.get_total_dwell()}s")
            return session
    
    def mark_reentry(self, visitor_id: str) -> Optional[VisitorSession]:
        """
        Mark session as re-entry.
        
        Args:
            visitor_id: Visitor ID
            
        Returns:
            Session or None if not found
        """
        with self._lock:
            if visitor_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[visitor_id]
            session.is_reentry = True
            session.reentry_count += 1
            
            logger.debug(f"Marked re-entry for {visitor_id}")
            return session
    
    def get_session(self, visitor_id: str) -> Optional[VisitorSession]:
        """Get session by visitor ID."""
        with self._lock:
            return self.active_sessions.get(visitor_id)
    
    def get_active_sessions(self) -> List[VisitorSession]:
        """Get all active sessions."""
        with self._lock:
            return list(self.active_sessions.values())
    
    def get_session_by_track(self, track_id: int) -> Optional[VisitorSession]:
        """Get session by track ID."""
        with self._lock:
            if track_id in self.track_to_visitor:
                visitor_id = self.track_to_visitor[track_id]
                return self.active_sessions.get(visitor_id)
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Close sessions that have exceeded timeout.
        
        Returns:
            Number of sessions closed
        """
        with self._lock:
            now = datetime.utcnow()
            expired = []
            
            for visitor_id, session in list(self.active_sessions.items()):
                if now - session.last_updated > self.session_timeout:
                    expired.append(visitor_id)
            
            for visitor_id in expired:
                self.close_session(visitor_id)
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            
            return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        with self._lock:
            return {
                'active_sessions': len(self.active_sessions),
                'completed_sessions': len(self.completed_sessions),
                'total_sessions': len(self.active_sessions) + len(self.completed_sessions),
                'avg_dwell_seconds': self._get_avg_dwell(),
                'conversion_rate': self._get_conversion_rate(),
                'reentry_rate': self._get_reentry_rate()
            }
    
    def _get_avg_dwell(self) -> float:
        """Calculate average dwell time."""
        if not self.completed_sessions:
            return 0.0
        
        total = sum(s.get_total_dwell() for s in self.completed_sessions)
        return total / len(self.completed_sessions)
    
    def _get_conversion_rate(self) -> float:
        """Calculate conversion rate."""
        if not self.completed_sessions:
            return 0.0
        
        conversions = sum(1 for s in self.completed_sessions if s.purchase_amount)
        return conversions / len(self.completed_sessions)
    
    def _get_reentry_rate(self) -> float:
        """Calculate re-entry rate."""
        if not self.completed_sessions:
            return 0.0
        
        reentries = sum(1 for s in self.completed_sessions if s.is_reentry)
        return reentries / len(self.completed_sessions)
    
    def reset(self) -> None:
        """Reset all sessions."""
        with self._lock:
            self.active_sessions.clear()
            self.completed_sessions.clear()
            self.track_to_visitor.clear()
            logger.info("SessionManager reset")
