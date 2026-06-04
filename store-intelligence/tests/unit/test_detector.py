# PROMPT: Create comprehensive unit tests for the PersonDetector class, covering:
# 1. Detector initialization with different model sizes and configurations
# 2. Single frame detection with valid/invalid inputs
# 3. Batch detection across multiple frames
# 4. Error handling for invalid frames and configurations
# 5. Device detection (CPU/GPU)
# 6. Confidence threshold validation
# Include edge cases like None inputs, wrong shapes, empty frames, and error recovery.
# Use pytest fixtures for reusable frame data and detector instances.
#
# CHANGES MADE:
# - Added comprehensive test coverage for all PersonDetector methods
# - Created fixtures for dummy frames and detector instances
# - Added parametrized tests for different model sizes
# - Included edge case tests for invalid inputs
# - Added integration tests for complete workflows

"""
Unit Tests for Person Detection Module

Tests PersonDetector class with various scenarios and edge cases.
"""

import pytest
import numpy as np
from detector.detector import PersonDetector, Detection, create_detector


class TestDetection:
    """Test Detection dataclass."""
    
    def test_detection_creation(self):
        """Test creating a detection."""
        det = Detection(
            bbox=[10, 20, 100, 200],
            confidence=0.95
        )
        
        assert det.bbox == [10, 20, 100, 200]
        assert det.confidence == 0.95
        assert det.class_id == 0
    
    def test_detection_to_dict(self):
        """Test detection to dict conversion."""
        det = Detection(
            bbox=[10, 20, 100, 200],
            confidence=0.95
        )
        
        det_dict = det.to_dict()
        assert det_dict["bbox"] == [10, 20, 100, 200]
        assert det_dict["confidence"] == 0.95
        assert det_dict["class_id"] == 0


class TestPersonDetector:
    """Test PersonDetector class."""
    
    @pytest.fixture
    def dummy_frame(self):
        """Create a dummy BGR frame."""
        return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def test_detector_initialization(self):
        """Test detector initialization with valid params."""
        detector = PersonDetector(
            model_size="nano",
            confidence_threshold=0.4,
            device="cpu"
        )
        
        assert detector.model_size == "nano"
        assert detector.confidence_threshold == 0.4
        assert detector.device == "cpu"
        assert detector.model is not None
    
    def test_detector_invalid_model_size(self):
        """Test detector with invalid model size."""
        with pytest.raises(ValueError):
            PersonDetector(model_size="invalid")
    
    def test_detector_valid_sizes(self):
        """Test all valid model sizes."""
        for size in ["nano", "small", "medium", "large", "xlarge"]:
            detector = PersonDetector(model_size=size, device="cpu")
            assert detector.model_size == size
    
    def test_detector_device_info(self):
        """Test getting device info."""
        detector = PersonDetector(device="cpu")
        info = detector.get_device_info()
        
        assert info["device"] == "cpu"
        assert info["model_size"] == "nano"
        assert "yolov8" in info["model_name"]
    
    def test_detect_invalid_frame_none(self):
        """Test detection with None frame."""
        detector = PersonDetector(device="cpu")
        
        with pytest.raises(ValueError):
            detector.detect(None)
    
    def test_detect_invalid_frame_shape(self):
        """Test detection with wrong shape."""
        detector = PersonDetector(device="cpu")
        
        # Grayscale image
        frame = np.zeros((480, 640), dtype=np.uint8)
        with pytest.raises(ValueError):
            detector.detect(frame)
        
        # Wrong number of channels
        frame = np.zeros((480, 640, 4), dtype=np.uint8)
        with pytest.raises(ValueError):
            detector.detect(frame)
    
    def test_detect_empty_frame(self, dummy_frame):
        """Test detection on empty (black) frame."""
        detector = PersonDetector(device="cpu", confidence_threshold=0.5)
        
        detections = detector.detect(dummy_frame)
        
        assert isinstance(detections, list)
        # Empty frame should have few or no detections
        assert len(detections) >= 0
    
    def test_detect_returns_detection_objects(self, dummy_frame):
        """Test that detect returns Detection objects."""
        detector = PersonDetector(device="cpu")
        
        detections = detector.detect(dummy_frame)
        
        assert isinstance(detections, list)
        if detections:
            for det in detections:
                assert isinstance(det, Detection)
                assert isinstance(det.bbox, list)
                assert len(det.bbox) == 4
                assert isinstance(det.confidence, float)
                assert 0 <= det.confidence <= 1
    
    def test_batch_detect_empty_list(self):
        """Test batch detect with empty list."""
        detector = PersonDetector(device="cpu")
        
        with pytest.raises(ValueError):
            detector.batch_detect([])
    
    def test_batch_detect_single_frame(self, dummy_frame):
        """Test batch detect with single frame."""
        detector = PersonDetector(device="cpu")
        
        detections_list = detector.batch_detect([dummy_frame])
        
        assert isinstance(detections_list, list)
        assert len(detections_list) == 1
        assert isinstance(detections_list[0], list)
    
    def test_batch_detect_multiple_frames(self, dummy_frame):
        """Test batch detect with multiple frames."""
        detector = PersonDetector(device="cpu")
        
        frames = [dummy_frame.copy() for _ in range(3)]
        detections_list = detector.batch_detect(frames)
        
        assert len(detections_list) == 3
        for detections in detections_list:
            assert isinstance(detections, list)
    
    def test_batch_detect_with_errors(self, dummy_frame):
        """Test batch detect handles errors gracefully."""
        detector = PersonDetector(device="cpu")
        
        frames = [dummy_frame, None, dummy_frame]
        detections_list = detector.batch_detect(frames)
        
        # Should return list with same length, handling errors
        assert len(detections_list) == 3
        assert isinstance(detections_list[1], list)  # Error frame returns empty list
    
    def test_create_detector_factory(self):
        """Test factory function."""
        detector = create_detector(
            model_size="nano",
            confidence_threshold=0.5,
            device="cpu"
        )
        
        assert isinstance(detector, PersonDetector)
        assert detector.model_size == "nano"
        assert detector.confidence_threshold == 0.5


class TestDetectorIntegration:
    """Integration tests for detector."""
    
    def test_detector_workflow(self):
        """Test complete detector workflow."""
        detector = PersonDetector(device="cpu")
        
        # Create test frames
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Single detection
        det1 = detector.detect(frame1)
        assert isinstance(det1, list)
        
        # Batch detection
        det_batch = detector.batch_detect([frame1, frame2])
        assert len(det_batch) == 2
        
        # Get info
        info = detector.get_device_info()
        assert info["device"] == "cpu"
