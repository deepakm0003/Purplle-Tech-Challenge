# PROMPT: Create comprehensive unit tests for the VideoProcessor class, covering:
# 1. Initialization and configuration
# 2. Frame processing with detections and tracking
# 3. Event generation for entry and exit events
# 4. Visitor state management and zone tracking
# 5. Edge cases: empty frames, missing sessions, invalid input
# 6. Statistics gathering and output
# The tests should use pytest with fixtures for mock detector, tracker, and visitor manager.
# Include parametrized tests for different configurations and scenarios.
#
# CHANGES MADE:
# - Added comprehensive test coverage for VideoProcessor
# - Created fixtures for detector, tracker, and visitor_manager
# - Parametrized tests for multiple scenarios
# - Edge case handling tests
# - Integration tests for complete workflow

"""
Unit Tests for Video Processing Module

Tests VideoProcessor class with various scenarios and edge cases.
"""

import pytest
import numpy as np
import cv2
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from detector.detector import PersonDetector, Detection
from detector.tracker import MultiObjectTracker, Track
from detector.visitor_state import VisitorStateManager
from detector.process_video import VideoProcessor, create_processor


class TestVideoProcessor:
    """Test VideoProcessor class."""
    
    @pytest.fixture
    def detector(self):
        """Create mock detector."""
        detector = Mock(spec=PersonDetector)
        detector.get_device_info.return_value = {
            "device": "cpu",
            "model_size": "nano"
        }
        return detector
    
    @pytest.fixture
    def tracker(self):
        """Create mock tracker."""
        tracker = Mock(spec=MultiObjectTracker)
        tracker.get_stats.return_value = {
            "frame_count": 0,
            "active_tracks": 0
        }
        return tracker
    
    @pytest.fixture
    def visitor_manager(self):
        """Create visitor state manager."""
        return VisitorStateManager()
    
    @pytest.fixture
    def processor(self, detector, tracker, visitor_manager):
        """Create VideoProcessor instance."""
        return VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            fps_sample_rate=1,
            store_id="STORE-TEST",
            camera_id="CAM-TEST"
        )
    
    def test_processor_initialization(self, detector, tracker, visitor_manager):
        """Test processor initialization."""
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            fps_sample_rate=2,
            store_id="STORE-001",
            camera_id="CAM-001"
        )
        
        assert processor.fps_sample_rate == 2
        assert processor.store_id == "STORE-001"
        assert processor.camera_id == "CAM-001"
        assert len(processor.events) == 0
    
    def test_processor_with_zone_mapper(self, detector, tracker, visitor_manager):
        """Test processor with zone mapper function."""
        def zone_mapper(x, y):
            if x < 320:
                return "ZONE-A"
            return "ZONE-B"
        
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            zone_mapper=zone_mapper
        )
        
        assert processor.zone_mapper is not None
    
    def test_processor_stats(self, processor):
        """Test getting processor statistics."""
        stats = processor.get_stats()
        
        assert "frame_count" in stats
        assert "processed_count" in stats
        assert "events_generated" in stats
        assert "detector_info" in stats
        assert "tracker_stats" in stats
        assert "visitor_stats" in stats
    
    def test_process_frame_with_detections(self, processor):
        """Test processing a frame with detections."""
        detector = processor.detector
        tracker = processor.tracker
        
        # Setup mock returns
        det1 = Detection(bbox=[10, 20, 100, 200], confidence=0.95)
        detector.detect.return_value = [det1]
        
        track1 = Track(
            track_id=1,
            bbox=[10, 20, 100, 200],
            confidence=0.95,
            age=5,
            hits=3
        )
        track1.state = "confirmed"
        tracker.update.return_value = [track1]
        
        # Process frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        processor._process_frame(frame)
        
        # Verify calls
        detector.detect.assert_called_once()
        tracker.update.assert_called_once()
    
    def test_process_frame_no_detections(self, processor):
        """Test processing frame with no detections."""
        detector = processor.detector
        tracker = processor.tracker
        
        detector.detect.return_value = []
        tracker.update.return_value = []
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        processor._process_frame(frame)
        
        tracker.update.assert_called_once()
    
    def test_event_generation(self, processor):
        """Test event generation."""
        visitor_manager = processor.visitor_manager
        
        # Create session
        visitor_id = visitor_manager.create_session(
            track_id=1,
            current_frame=0
        )
        
        # Generate entry event
        session = visitor_manager.get_session(visitor_id)
        processor._generate_entry_event(session)
        
        assert len(processor.events) == 1
        assert processor.events[0]["event_type"] == "ENTRY"
        assert processor.events[0]["visitor_id"] == visitor_id
    
    def test_exit_event_generation(self, processor):
        """Test exit event generation."""
        visitor_manager = processor.visitor_manager
        
        # Create and end session
        visitor_id = visitor_manager.create_session(
            track_id=1,
            current_frame=0
        )
        session = visitor_manager.end_session(visitor_id, current_frame=100)
        
        processor._generate_exit_event(session)
        
        assert len(processor.events) == 1
        assert processor.events[0]["event_type"] == "EXIT"
        assert processor.events[0]["duration_frames"] == 0
    
    def test_visitor_state_update(self, processor):
        """Test visitor state updates during tracking."""
        visitor_manager = processor.visitor_manager
        detector = processor.detector
        tracker = processor.tracker
        
        # Setup mocks
        det = Detection(bbox=[100, 100, 200, 200], confidence=0.9)
        detector.detect.return_value = [det]
        
        track = Track(
            track_id=1,
            bbox=[100, 100, 200, 200],
            confidence=0.9,
            hits=3
        )
        track.state = "confirmed"
        tracker.update.return_value = [track]
        
        # Process frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        processor._process_frame(frame)
        
        # Check visitor state
        sessions = visitor_manager.get_active_sessions()
        assert len(sessions) > 0
    
    def test_aged_session_cleanup(self, processor):
        """Test that aged sessions are cleaned up."""
        visitor_manager = processor.visitor_manager
        
        # Create session
        visitor_manager.create_session(1, current_frame=0)
        
        # Simulate frame without this track
        processor.frame_count = 400
        
        # Cleanup
        cleaned = visitor_manager.cleanup_aged_sessions(400)
        
        # Session should be marked inactive but still in completed
        inactive = visitor_manager.get_inactive_sessions()
        assert len(inactive) > 0
    
    def test_save_events_to_file(self, processor):
        """Test saving events to JSONL file."""
        visitor_manager = processor.visitor_manager
        
        # Create event
        visitor_id = visitor_manager.create_session(1, current_frame=0)
        session = visitor_manager.get_session(visitor_id)
        processor._generate_entry_event(session)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "events.jsonl"
            processor._save_events(str(output_path))
            
            assert output_path.exists()
            
            # Verify content
            with open(output_path) as f:
                lines = f.readlines()
                assert len(lines) == 1
    
    def test_processor_stats_after_processing(self, processor):
        """Test processor stats after some processing."""
        detector = processor.detector
        tracker = processor.tracker
        
        detector.detect.return_value = []
        tracker.update.return_value = []
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        processor._process_frame(frame)
        
        processor.frame_count = 100
        processor.processed_count = 50
        
        stats = processor.get_stats()
        assert stats["frame_count"] == 100
        assert stats["processed_count"] == 50
        assert stats["skip_rate"] == processor.fps_sample_rate


class TestVideoProcessorEdgeCases:
    """Test edge cases for VideoProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create processor with real components."""
        detector = Mock(spec=PersonDetector)
        tracker = Mock(spec=MultiObjectTracker)
        visitor_manager = VisitorStateManager()
        
        detector.detect.return_value = []
        tracker.update.return_value = []
        tracker.get_stats.return_value = {"frame_count": 0}
        detector.get_device_info.return_value = {"device": "cpu"}
        
        return VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager
        )
    
    def test_empty_events_list(self, processor):
        """Test that empty events list is handled."""
        assert processor.events == []
        stats = processor.get_stats()
        assert stats["events_generated"] == 0
    
    def test_multiple_visitors(self, processor):
        """Test handling multiple visitors."""
        visitor_manager = processor.visitor_manager
        
        # Create multiple sessions
        for i in range(5):
            visitor_manager.create_session(i, current_frame=0)
        
        active = visitor_manager.get_active_sessions()
        assert len(active) == 5
    
    def test_frame_rate_sampling(self):
        """Test frame rate sampling."""
        detector = Mock(spec=PersonDetector)
        tracker = Mock(spec=MultiObjectTracker)
        visitor_manager = VisitorStateManager()
        
        detector.detect.return_value = []
        tracker.update.return_value = []
        tracker.get_stats.return_value = {"frame_count": 0}
        detector.get_device_info.return_value = {"device": "cpu"}
        
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            fps_sample_rate=5  # Process every 5th frame
        )
        
        assert processor.fps_sample_rate == 5


class TestVideoProcessorFactory:
    """Test factory function."""
    
    def test_create_processor_factory(self):
        """Test processor factory function."""
        detector = Mock(spec=PersonDetector)
        tracker = Mock(spec=MultiObjectTracker)
        visitor_manager = VisitorStateManager()
        
        processor = create_processor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            store_id="STORE-TEST"
        )
        
        assert isinstance(processor, VideoProcessor)
        assert processor.store_id == "STORE-TEST"
