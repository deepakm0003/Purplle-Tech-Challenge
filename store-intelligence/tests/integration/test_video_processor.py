"""
Integration Tests for Video Processor

Tests complete video processing pipeline.
"""

import pytest
import numpy as np
import tempfile
import json
import os
from pathlib import Path

from detector.detector import PersonDetector
from detector.tracker import MultiObjectTracker
from detector.visitor_state import VisitorStateManager
from detector.process_video import VideoProcessor, create_processor


class TestVideoProcessor:
    """Test VideoProcessor class."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return PersonDetector(device="cpu")
    
    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return MultiObjectTracker()
    
    @pytest.fixture
    def visitor_manager(self):
        """Create visitor manager."""
        return VisitorStateManager()
    
    @pytest.fixture
    def processor(self, detector, tracker, visitor_manager):
        """Create processor instance."""
        return VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            fps_sample_rate=5,
            store_id="STORE-001",
            camera_id="CAM-001"
        )
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.detector is not None
        assert processor.tracker is not None
        assert processor.visitor_manager is not None
        assert processor.store_id == "STORE-001"
        assert processor.camera_id == "CAM-001"
    
    def test_processor_stats(self, processor):
        """Test processor statistics."""
        stats = processor.get_stats()
        
        assert "frame_count" in stats
        assert "processed_count" in stats
        assert "events_generated" in stats
        assert "detector_info" in stats
        assert "tracker_stats" in stats
        assert "visitor_stats" in stats
    
    def test_create_processor_factory(self, detector, tracker, visitor_manager):
        """Test factory function."""
        processor = create_processor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            store_id="STORE-002"
        )
        
        assert isinstance(processor, VideoProcessor)
        assert processor.store_id == "STORE-002"
    
    def test_processor_with_zone_mapper(self, detector, tracker, visitor_manager):
        """Test processor with zone mapper."""
        def zone_mapper(x, y):
            if x < 320:
                return 1
            else:
                return 2
        
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager,
            zone_mapper=zone_mapper
        )
        
        assert processor.zone_mapper is not None
    
    def test_save_events(self, processor):
        """Test saving events to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "events.jsonl")
            
            # Create some mock events
            processor.events = [
                {
                    "event_id": "evt_1",
                    "event_type": "ENTRY",
                    "visitor_id": "v1",
                    "timestamp": "2024-01-01T00:00:00"
                },
                {
                    "event_id": "evt_2",
                    "event_type": "EXIT",
                    "visitor_id": "v1",
                    "timestamp": "2024-01-01T00:01:00"
                }
            ]
            
            processor._save_events(output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            
            # Verify content
            with open(output_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
                
                event1 = json.loads(lines[0])
                event2 = json.loads(lines[1])
                
                assert event1["event_type"] == "ENTRY"
                assert event2["event_type"] == "EXIT"
    
    def test_processor_generate_entry_event(self, processor):
        """Test entry event generation."""
        session = processor.visitor_manager.create_session(
            track_id=1,
            current_frame=0
        )
        
        processor._generate_entry_event(session)
        
        assert len(processor.events) == 1
        event = processor.events[0]
        assert event["event_type"] == "ENTRY"
        assert event["visitor_id"] == session.visitor_id
    
    def test_processor_generate_exit_event(self, processor):
        """Test exit event generation."""
        session = processor.visitor_manager.create_session(
            track_id=1,
            current_frame=0
        )
        
        processor._generate_exit_event(session)
        
        assert len(processor.events) == 1
        event = processor.events[0]
        assert event["event_type"] == "EXIT"


class TestVideoProcessingPipeline:
    """Integration tests for complete pipeline."""
    
    def create_test_video(self, video_path: str, num_frames: int = 30):
        """Create a test video file."""
        import cv2
        
        width, height = 640, 480
        fps = 30
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        
        for _ in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Add some variation to frames
            frame[:, :, 0] = np.random.randint(0, 100)
            out.write(frame)
        
        out.release()
    
    def test_pipeline_with_dummy_video(self):
        """Test complete pipeline with dummy video."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test video
            video_path = os.path.join(tmpdir, "test.mp4")
            self.create_test_video(video_path, num_frames=30)
            
            # Create processor
            detector = PersonDetector(device="cpu")
            tracker = MultiObjectTracker()
            visitor_manager = VisitorStateManager()
            
            processor = VideoProcessor(
                detector=detector,
                tracker=tracker,
                visitor_manager=visitor_manager,
                fps_sample_rate=2
            )
            
            # Process video
            event_count, events = processor.process_video(
                video_path,
                show_progress=False
            )
            
            # Verify processing
            assert processor.frame_count > 0
            assert processor.processed_count > 0
            
            stats = processor.get_stats()
            assert stats["frame_count"] == 30
            assert stats["processed_count"] > 0
    
    def test_pipeline_saves_events(self):
        """Test pipeline saves events to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test video
            video_path = os.path.join(tmpdir, "test.mp4")
            output_path = os.path.join(tmpdir, "events.jsonl")
            
            self.create_test_video(video_path, num_frames=20)
            
            # Create processor
            detector = PersonDetector(device="cpu")
            tracker = MultiObjectTracker()
            visitor_manager = VisitorStateManager()
            
            processor = VideoProcessor(
                detector=detector,
                tracker=tracker,
                visitor_manager=visitor_manager
            )
            
            # Process and save
            processor.process_video(
                video_path,
                output_path=output_path,
                show_progress=False
            )
            
            # Verify file exists and contains valid events
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    event = json.loads(line)
                    assert "event_id" in event
                    assert "event_type" in event


class TestProcessorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_processor_invalid_video_path(self):
        """Test processing non-existent video."""
        detector = PersonDetector(device="cpu")
        tracker = MultiObjectTracker()
        visitor_manager = VisitorStateManager()
        
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager
        )
        
        with pytest.raises(FileNotFoundError):
            processor.process_video("/path/to/nonexistent/video.mp4")
    
    def test_processor_empty_events(self):
        """Test processor with no detections."""
        detector = PersonDetector(device="cpu")
        tracker = MultiObjectTracker()
        visitor_manager = VisitorStateManager()
        
        processor = VideoProcessor(
            detector=detector,
            tracker=tracker,
            visitor_manager=visitor_manager
        )
        
        # Create empty events list
        processor.events = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "events.jsonl")
            processor._save_events(output_path)
            
            # File should exist but be empty
            assert os.path.exists(output_path)
            with open(output_path, 'r') as f:
                content = f.read()
                assert content == ""
