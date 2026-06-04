"""
Unit Tests for Visitor State Management

Tests VisitorStateManager and VisitorSession classes.
"""

import pytest
from detector.visitor_state import VisitorStateManager, VisitorSession, create_visitor_manager


class TestVisitorSession:
    """Test VisitorSession dataclass."""
    
    def test_session_creation(self):
        """Test creating a visitor session."""
        session = VisitorSession(
            visitor_id="visitor_1",
            session_id="session_1",
            track_id=1,
            first_seen_frame=0,
            last_seen_frame=0
        )
        
        assert session.visitor_id == "visitor_1"
        assert session.session_id == "session_1"
        assert session.track_id == 1
        assert session.active is True
    
    def test_session_get_dwell_time(self):
        """Test getting dwell time for zone."""
        session = VisitorSession(
            visitor_id="visitor_1",
            session_id="session_1",
            track_id=1,
            first_seen_frame=0,
            last_seen_frame=100
        )
        
        # Add dwell time
        session.dwell_times[1] = 50
        
        assert session.get_dwell_time(1) == 50
        assert session.get_dwell_time(2) == 0
    
    def test_session_to_dict(self):
        """Test session to dict conversion."""
        session = VisitorSession(
            visitor_id="visitor_1",
            session_id="session_1",
            track_id=1,
            first_seen_frame=0,
            last_seen_frame=100
        )
        
        session_dict = session.to_dict()
        assert session_dict["visitor_id"] == "visitor_1"
        assert session_dict["track_id"] == 1
        assert session_dict["active"] is True


class TestVisitorStateManager:
    """Test VisitorStateManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return VisitorStateManager(session_timeout=300)
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = VisitorStateManager(session_timeout=300)
        
        assert manager.session_timeout == 300
        assert len(manager.sessions) == 0
        assert len(manager.visitor_sessions) == 0
    
    def test_create_session(self, manager):
        """Test creating a session."""
        session = manager.create_session(
            track_id=1,
            current_frame=0,
            visitor_id="visitor_1"
        )
        
        assert session.track_id == 1
        assert session.visitor_id == "visitor_1"
        assert session.first_seen_frame == 0
    
    def test_create_session_auto_id(self, manager):
        """Test creating session with auto-generated visitor ID."""
        session = manager.create_session(
            track_id=1,
            current_frame=0
        )
        
        assert session.visitor_id is not None
        assert len(session.visitor_id) > 0
    
    def test_get_session(self, manager):
        """Test getting a session."""
        manager.create_session(track_id=1, current_frame=0)
        
        session = manager.get_session(1)
        assert session is not None
        assert session.track_id == 1
    
    def test_update_session(self, manager):
        """Test updating a session."""
        manager.create_session(track_id=1, current_frame=0)
        
        updated = manager.update_session(
            track_id=1,
            current_frame=10,
            zone_id=5
        )
        
        assert updated is not None
        assert updated.last_seen_frame == 10
        assert 5 in updated.zones_visited
    
    def test_update_session_zone_transition(self, manager):
        """Test zone transitions."""
        manager.create_session(track_id=1, current_frame=0, visitor_id="v1")
        
        # Enter zone 1
        manager.update_session(1, 10, zone_id=1)
        session = manager.get_session(1)
        assert session.current_zone == 1
        
        # Move to zone 2
        manager.update_session(1, 20, zone_id=2)
        session = manager.get_session(1)
        assert session.current_zone == 2
        # Zone 1 dwell should be recorded
        assert 1 in session.dwell_times
    
    def test_end_session(self, manager):
        """Test ending a session."""
        manager.create_session(track_id=1, current_frame=0)
        
        ended = manager.end_session(track_id=1, current_frame=100)
        
        assert ended is not None
        assert ended.active is False
        assert ended.last_seen_frame == 100
    
    def test_get_active_sessions(self, manager):
        """Test getting active sessions."""
        manager.create_session(track_id=1, current_frame=0)
        manager.create_session(track_id=2, current_frame=0)
        
        active = manager.get_active_sessions()
        assert len(active) == 2
    
    def test_get_inactive_sessions(self, manager):
        """Test getting inactive sessions."""
        manager.create_session(track_id=1, current_frame=0)
        manager.end_session(track_id=1, current_frame=10)
        
        inactive = manager.get_inactive_sessions()
        assert len(inactive) == 1
    
    def test_get_visitor_sessions(self, manager):
        """Test getting all sessions for a visitor."""
        visitor_id = "visitor_1"
        
        manager.create_session(track_id=1, current_frame=0, visitor_id=visitor_id)
        manager.create_session(track_id=2, current_frame=0, visitor_id=visitor_id)
        
        sessions = manager.get_visitor_sessions(visitor_id)
        assert len(sessions) == 2
    
    def test_cleanup_aged_sessions(self, manager):
        """Test cleaning up aged sessions."""
        manager.create_session(track_id=1, current_frame=0)
        
        # Move beyond timeout
        cleaned = manager.cleanup_aged_sessions(
            current_frame=manager.session_timeout + 10
        )
        
        assert cleaned > 0
        session = manager.get_session(1)
        assert session.active is False
    
    def test_manager_stats(self, manager):
        """Test manager statistics."""
        manager.create_session(track_id=1, current_frame=0)
        manager.create_session(track_id=2, current_frame=0)
        
        stats = manager.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2
        assert stats["inactive_sessions"] == 0
    
    def test_manager_reset(self, manager):
        """Test resetting manager."""
        manager.create_session(track_id=1, current_frame=0)
        manager.create_session(track_id=2, current_frame=0)
        
        assert len(manager.sessions) == 2
        
        manager.reset()
        
        assert len(manager.sessions) == 0
        assert len(manager.visitor_sessions) == 0
    
    def test_thread_safety(self, manager):
        """Test thread-safe operations."""
        import threading
        
        def create_sessions():
            for i in range(10):
                manager.create_session(track_id=i, current_frame=i)
        
        threads = [threading.Thread(target=create_sessions) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have sessions from all threads
        assert len(manager.sessions) >= 10
    
    def test_create_visitor_manager_factory(self):
        """Test factory function."""
        manager = create_visitor_manager(session_timeout=600)
        
        assert isinstance(manager, VisitorStateManager)
        assert manager.session_timeout == 600


class TestVisitorStateIntegration:
    """Integration tests for visitor state management."""
    
    def test_visitor_session_workflow(self):
        """Test complete visitor session workflow."""
        manager = VisitorStateManager()
        
        # Create session
        session = manager.create_session(
            track_id=1,
            current_frame=0,
            visitor_id="visitor_1"
        )
        
        assert session.active is True
        
        # Update in various zones
        manager.update_session(1, 10, zone_id=1)
        manager.update_session(1, 20, zone_id=2)
        manager.update_session(1, 30, zone_id=1)
        
        session = manager.get_session(1)
        assert 1 in session.zones_visited
        assert 2 in session.zones_visited
        
        # End session
        manager.end_session(1, 40)
        
        session = manager.get_session(1)
        assert not session.active
        assert session.get_dwell_time(1) > 0
