"""
Unit Tests for SessionManager

Tests session lifecycle, zone tracking, dwell calculations,
and statistics generation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from detector.session_manager import SessionManager, VisitorSession


class TestVisitorSession:
    """Tests for VisitorSession dataclass."""
    
    def test_session_initialization(self):
        """Test VisitorSession initialization."""
        visitor_id = "VIS_test123"
        track_id = 42
        
        session = VisitorSession(visitor_id, track_id)
        
        assert session.visitor_id == visitor_id
        assert session.track_id == track_id
        assert session.entry_time is not None
        assert session.exit_time is None
        assert session.is_active is True
        assert len(session.zones_visited) == 0
        assert session.zone_dwell_times == {}
    
    def test_session_to_dict(self):
        """Test session conversion to dictionary."""
        session = VisitorSession("VIS_test", 1)
        
        d = session.to_dict()
        
        assert d['visitor_id'] == "VIS_test"
        assert d['track_id'] == 1
        assert d['is_active'] is True
        assert 'entry_time' in d
        assert 'total_dwell_seconds' in d
    
    def test_get_total_dwell_active(self):
        """Test dwell time for active session."""
        session = VisitorSession("VIS_test", 1)
        
        # Should calculate from now
        dwell = session.get_total_dwell()
        
        assert dwell >= 0
        assert isinstance(dwell, int)
    
    def test_get_total_dwell_closed(self):
        """Test dwell time for closed session."""
        session = VisitorSession("VIS_test", 1)
        session.exit_time = session.entry_time + timedelta(seconds=100)
        
        dwell = session.get_total_dwell()
        
        assert dwell == 100
    
    def test_get_zone_dwell(self):
        """Test zone-specific dwell time."""
        session = VisitorSession("VIS_test", 1)
        session.zone_dwell_times = {"ZONE_A": 30, "ZONE_B": 45}
        
        assert session.get_zone_dwell("ZONE_A") == 30
        assert session.get_zone_dwell("ZONE_B") == 45
        assert session.get_zone_dwell("ZONE_C") == 0


class TestSessionManager:
    """Tests for SessionManager."""
    
    def test_manager_initialization(self):
        """Test SessionManager initialization."""
        manager = SessionManager(session_timeout_minutes=5)
        
        assert manager.session_timeout == timedelta(minutes=5)
        assert len(manager.active_sessions) == 0
        assert len(manager.completed_sessions) == 0
    
    def test_start_session_auto_visitor_id(self):
        """Test starting session with auto-generated visitor ID."""
        manager = SessionManager()
        
        session = manager.start_session(track_id=1)
        
        assert session.visitor_id.startswith("VIS_")
        assert session.track_id == 1
        assert session.visitor_id in manager.active_sessions
        assert 1 in manager.track_to_visitor.values()
    
    def test_start_session_explicit_visitor_id(self):
        """Test starting session with explicit visitor ID."""
        manager = SessionManager()
        
        session = manager.start_session(track_id=1, visitor_id="VIS_custom")
        
        assert session.visitor_id == "VIS_custom"
        assert manager.active_sessions["VIS_custom"] == session
    
    def test_update_session_new_zone(self):
        """Test zone transition in session."""
        manager = SessionManager()
        session = manager.start_session(1)
        visitor_id = session.visitor_id
        
        # Enter first zone
        manager.update_session(visitor_id, "ZONE_A")
        
        session = manager.get_session(visitor_id)
        assert session.current_zone == "ZONE_A"
        assert "ZONE_A" in session.zones_visited
        assert "ZONE_A" in session.zone_entry_times
    
    def test_update_session_zone_transition(self):
        """Test zone transition (enter new zone while in another)."""
        manager = SessionManager()
        session = manager.start_session(1)
        visitor_id = session.visitor_id
        
        # Enter first zone
        manager.update_session(visitor_id, "ZONE_A")
        first_session = manager.get_session(visitor_id)
        assert first_session.current_zone == "ZONE_A"
        
        # Transition to second zone (simulate time passing)
        first_session.zone_entry_times["ZONE_A"] = datetime.utcnow() - timedelta(seconds=10)
        manager.update_session(visitor_id, "ZONE_B")
        
        updated = manager.get_session(visitor_id)
        assert updated.current_zone == "ZONE_B"
        assert "ZONE_B" in updated.zones_visited
        assert "ZONE_A" in updated.zone_dwell_times
        assert updated.zone_dwell_times["ZONE_A"] >= 10
    
    def test_close_session(self):
        """Test closing a session."""
        manager = SessionManager()
        session = manager.start_session(1)
        visitor_id = session.visitor_id
        
        manager.update_session(visitor_id, "ZONE_A")
        closed = manager.close_session(visitor_id)
        
        assert closed is not None
        assert closed.is_active is False
        assert closed.exit_time is not None
        assert visitor_id not in manager.active_sessions
        assert closed in manager.completed_sessions
    
    def test_close_nonexistent_session(self):
        """Test closing non-existent session."""
        manager = SessionManager()
        
        result = manager.close_session("VIS_nonexistent")
        
        assert result is None
    
    def test_mark_reentry(self):
        """Test marking session as re-entry."""
        manager = SessionManager()
        session = manager.start_session(1)
        visitor_id = session.visitor_id
        
        manager.mark_reentry(visitor_id)
        updated = manager.get_session(visitor_id)
        
        assert updated.is_reentry is True
        assert updated.reentry_count == 1
    
    def test_get_session_by_track(self):
        """Test retrieving session by track ID."""
        manager = SessionManager()
        session = manager.start_session(track_id=42)
        
        found = manager.get_session_by_track(42)
        
        assert found == session
        assert found.track_id == 42
    
    def test_cleanup_expired_sessions(self):
        """Test expiring old sessions."""
        manager = SessionManager(session_timeout_minutes=1)
        
        session1 = manager.start_session(1)
        visitor_id_1 = session1.visitor_id
        
        session2 = manager.start_session(2)
        visitor_id_2 = session2.visitor_id
        
        # Age first session beyond timeout
        manager.active_sessions[visitor_id_1].last_updated = (
            datetime.utcnow() - timedelta(minutes=2)
        )
        
        expired_count = manager.cleanup_expired_sessions()
        
        assert expired_count == 1
        assert visitor_id_1 not in manager.active_sessions
        assert visitor_id_2 in manager.active_sessions
        assert len(manager.completed_sessions) >= 1
    
    def test_get_active_sessions(self):
        """Test retrieving all active sessions."""
        manager = SessionManager()
        
        manager.start_session(1)
        manager.start_session(2)
        manager.start_session(3)
        
        active = manager.get_active_sessions()
        
        assert len(active) == 3
    
    def test_get_stats(self):
        """Test statistics calculation."""
        manager = SessionManager()
        
        # Start and close a session
        session = manager.start_session(1)
        visitor_id = session.visitor_id
        manager.update_session(visitor_id, "ZONE_A")
        manager.close_session(visitor_id)
        
        stats = manager.get_stats()
        
        assert stats['active_sessions'] == 0
        assert stats['completed_sessions'] == 1
        assert stats['total_sessions'] == 1
        assert 'avg_dwell_seconds' in stats
        assert 'conversion_rate' in stats
        assert 'reentry_rate' in stats
    
    def test_thread_safety_concurrent_sessions(self):
        """Test that concurrent operations are thread-safe."""
        import threading
        
        manager = SessionManager()
        
        def create_and_close():
            session = manager.start_session(
                track_id=int(threading.current_thread().name.split('-')[1])
            )
            visitor_id = session.visitor_id
            manager.update_session(visitor_id, "ZONE_A")
            manager.close_session(visitor_id)
        
        threads = [threading.Thread(target=create_and_close) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(manager.completed_sessions) == 10
    
    def test_reset(self):
        """Test resetting manager state."""
        manager = SessionManager()
        
        manager.start_session(1)
        manager.start_session(2)
        
        assert len(manager.active_sessions) == 2
        
        manager.reset()
        
        assert len(manager.active_sessions) == 0
        assert len(manager.completed_sessions) == 0
        assert len(manager.track_to_visitor) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
