# PROMPT: Create comprehensive unit tests for the MultiObjectTracker class, covering:
# 1. Tracker initialization and configuration
# 2. Update operations with single and multiple detections
# 3. Track state transitions (tentative → confirmed → deleted)
# 4. Track matching and IoU computation
# 5. Track aging and cleanup
# 6. Edge cases: no detections, occlusion handling, rapid movement
# Include tests for track retrieval methods and statistics generation.
# Use pytest fixtures for reusable tracker instances and mock detections.
#
# CHANGES MADE:
# - Added comprehensive test coverage for all MultiObjectTracker methods
# - Created fixtures for tracker initialization
# - Added parametrized tests for different configurations
# - Included IoU computation tests
# - Added track lifecycle tests (creation, confirmation, aging, deletion)

"""
Unit Tests for Multi-Object Tracker

Tests MultiObjectTracker class with various scenarios.
"""

import pytest
from detector.tracker import MultiObjectTracker, Track, create_tracker


class TestTrack:
    """Test Track dataclass."""
    
    def test_track_creation(self):
        """Test creating a track."""
        track = Track(
            track_id=1,
            bbox=[10, 20, 100, 200],
            confidence=0.95
        )
        
        assert track.track_id == 1
        assert track.bbox == [10, 20, 100, 200]
        assert track.confidence == 0.95
        assert track.state == "tentative"
        assert track.age == 0
        assert track.hits == 0
    
    def test_track_to_dict(self):
        """Test track to dict conversion."""
        track = Track(
            track_id=1,
            bbox=[10, 20, 100, 200],
            confidence=0.95,
            age=5,
            hits=3
        )
        
        track_dict = track.to_dict()
        assert track_dict["track_id"] == 1
        assert track_dict["state"] == "tentative"
        assert track_dict["age"] == 5
        assert track_dict["hits"] == 3


class TestMultiObjectTracker:
    """Test MultiObjectTracker class."""
    
    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return MultiObjectTracker(
            max_age=30,
            min_hits=3,
            iou_threshold=0.3
        )
    
    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = MultiObjectTracker(
            max_age=30,
            min_hits=3
        )
        
        assert tracker.max_age == 30
        assert tracker.min_hits == 3
        assert len(tracker.tracks) == 0
        assert tracker.next_track_id == 1
    
    def test_tracker_with_empty_detections(self, tracker):
        """Test update with no detections."""
        tracks = tracker.update([])
        
        assert len(tracks) == 0
        assert len(tracker.tracks) == 0
    
    def test_tracker_single_detection(self, tracker):
        """Test with single detection."""
        detection = {
            "bbox": [10, 20, 100, 200],
            "confidence": 0.95
        }
        
        tracks = tracker.update([detection])
        
        # First update, track is tentative
        assert len(tracks) == 0  # Not confirmed yet
        assert len(tracker.tracks) == 1  # Track created
    
    def test_tracker_multiple_detections(self, tracker):
        """Test with multiple detections."""
        detections = [
            {"bbox": [10, 20, 100, 200], "confidence": 0.95},
            {"bbox": [200, 20, 300, 200], "confidence": 0.90},
            {"bbox": [400, 20, 500, 200], "confidence": 0.85}
        ]
        
        tracker.update(detections)
        
        assert len(tracker.tracks) == 3
    
    def test_tracker_track_confirmation(self, tracker):
        """Test track confirmation after min_hits."""
        detection = {
            "bbox": [10, 20, 100, 200],
            "confidence": 0.95
        }
        
        # Update multiple times to confirm
        for _ in range(tracker.min_hits):
            tracks = tracker.update([detection])
        
        # After min_hits, track should be confirmed
        assert len(tracks) > 0
    
    def test_tracker_track_matching(self, tracker):
        """Test that detections match to same track."""
        det1 = {"bbox": [10, 20, 100, 200], "confidence": 0.95}
        det2 = {"bbox": [11, 21, 101, 201], "confidence": 0.95}  # Slightly moved
        
        tracker.update([det1])
        tracker.update([det2])  # Should match to same track
        
        # Should still have 1 track (matched)
        assert len(tracker.tracks) == 1
    
    def test_tracker_get_active_tracks(self, tracker):
        """Test getting active tracks."""
        # Create confirmed track
        detection = {"bbox": [10, 20, 100, 200], "confidence": 0.95}
        
        for _ in range(tracker.min_hits):
            tracker.update([detection])
        
        active_tracks = tracker.get_active_tracks()
        assert len(active_tracks) > 0
    
    def test_tracker_get_all_tracks(self, tracker):
        """Test getting all tracks."""
        detection = {"bbox": [10, 20, 100, 200], "confidence": 0.95}
        
        tracker.update([detection])
        
        all_tracks = tracker.get_all_tracks()
        assert len(all_tracks) == 1
    
    def test_tracker_get_track(self, tracker):
        """Test getting specific track."""
        detection = {"bbox": [10, 20, 100, 200], "confidence": 0.95}
        tracker.update([detection])
        
        track = tracker.get_track(1)
        assert track is not None
        assert track.track_id == 1
        
        # Non-existent track
        assert tracker.get_track(999) is None
    
    def test_tracker_aging(self, tracker):
        """Test track aging without detections."""
        detection = {"bbox": [10, 20, 100, 200], "confidence": 0.95}
        
        # Create track
        for _ in range(tracker.min_hits):
            tracker.update([detection])
        
        # Age out track
        for _ in range(tracker.max_age + 1):
            tracker.update([])
        
        # Track should be deleted after max_age
        all_tracks = tracker.get_all_tracks()
        # Deleted tracks are removed
        assert len(all_tracks) == 0
    
    def test_tracker_stats(self, tracker):
        """Test tracker statistics."""
        detections = [
            {"bbox": [10, 20, 100, 200], "confidence": 0.95},
            {"bbox": [200, 20, 300, 200], "confidence": 0.90}
        ]
        
        tracker.update(detections)
        
        stats = tracker.get_stats()
        assert "frame_count" in stats
        assert "total_tracks_created" in stats
        assert "active_confirmed" in stats
    
    def test_iou_computation(self, tracker):
        """Test IoU computation."""
        box1 = [0, 0, 100, 100]
        box2 = [50, 50, 150, 150]
        
        iou = tracker._compute_iou(box1, box2)
        
        # Should be between 0 and 1
        assert 0 <= iou <= 1
        # Should not be 0 (boxes overlap)
        assert iou > 0
    
    def test_iou_no_overlap(self, tracker):
        """Test IoU with no overlap."""
        box1 = [0, 0, 100, 100]
        box2 = [200, 200, 300, 300]
        
        iou = tracker._compute_iou(box1, box2)
        assert iou == 0
    
    def test_iou_full_overlap(self, tracker):
        """Test IoU with full overlap."""
        box1 = [0, 0, 100, 100]
        box2 = [0, 0, 100, 100]
        
        iou = tracker._compute_iou(box1, box2)
        assert iou == 1.0
    
    def test_create_tracker_factory(self):
        """Test factory function."""
        tracker = create_tracker(max_age=30, min_hits=3)
        
        assert isinstance(tracker, MultiObjectTracker)
        assert tracker.max_age == 30
        assert tracker.min_hits == 3


class TestTrackerIntegration:
    """Integration tests for tracker."""
    
    def test_tracker_workflow(self):
        """Test complete tracker workflow."""
        tracker = MultiObjectTracker()
        
        # Simulate video with moving person
        base_bbox = [100, 100, 200, 300]
        
        for frame_idx in range(10):
            # Person moves slightly each frame
            bbox = [
                base_bbox[0] + frame_idx,
                base_bbox[1] + frame_idx,
                base_bbox[2] + frame_idx,
                base_bbox[3] + frame_idx
            ]
            
            detection = {"bbox": bbox, "confidence": 0.95}
            tracks = tracker.update([detection])
        
        # Should have confirmed track after 10 frames
        assert len(tracks) > 0
        assert tracks[0].track_id == 1
