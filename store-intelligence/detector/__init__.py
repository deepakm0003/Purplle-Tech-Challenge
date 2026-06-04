"""
Detection and Tracking Pipeline Module

Implements complete detection, tracking, and visitor state management pipeline
for analyzing CCTV video footage.

Components:
- PersonDetector: YOLOv8 person detection
- MultiObjectTracker: ByteTrack-based multi-object tracking
- VisitorStateManager: Visitor session and state management
- VideoProcessor: Complete video processing pipeline
"""

from .detector import PersonDetector, Detection, create_detector
from .tracker import MultiObjectTracker, Track, create_tracker
from .visitor_state import VisitorStateManager, VisitorSession, create_visitor_manager
from .process_video import VideoProcessor, create_processor

__all__ = [
    "PersonDetector",
    "Detection",
    "create_detector",
    "MultiObjectTracker",
    "Track",
    "create_tracker",
    "VisitorStateManager",
    "VisitorSession",
    "create_visitor_manager",
    "VideoProcessor",
    "create_processor",
]

