"""
ByteTrack Multi-Object Tracking Module

Implements ByteTrack for robust person tracking across video frames.
Handles occlusion, crowded scenes, and group entry/exit.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


@dataclass
class Track:
    """
    Represents a tracked person across frames.
    
    Attributes:
        track_id: Unique track identifier
        bbox: [x1, y1, x2, y2] bounding box
        confidence: Detection confidence
        age: Number of frames since track was created
        hits: Number of frames with confirmed detections
        time_since_update: Frames since last detection
        state: 'tentative', 'confirmed', or 'deleted'
        trajectory: List of (frame_id, bbox) tuples
    """
    
    track_id: int
    bbox: List[float]
    confidence: float
    age: int = 0
    hits: int = 0
    time_since_update: int = 0
    state: str = "tentative"  # tentative, confirmed, deleted
    trajectory: List[tuple] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary."""
        return {
            "track_id": self.track_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "age": self.age,
            "hits": self.hits,
            "state": self.state,
            "trajectory_length": len(self.trajectory)
        }


class MultiObjectTracker:
    """
    ByteTrack-based Multi-Object Tracker.
    
    Robust tracking using IoU-based matching with support for:
    - Occlusion handling
    - Crowded scene tracking
    - Group entry/exit
    - High-motion scenarios
    
    Attributes:
        max_age: Max frames to keep track alive without detections
        min_hits: Min detections to confirm track
        iou_threshold: IoU threshold for matching
        high_det_thresh: High detection confidence threshold
        low_det_thresh: Low detection confidence threshold
    """
    
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        high_det_thresh: float = 0.5,
        low_det_thresh: float = 0.1,
        min_motion_pixels: float = 12.0,
    ):
        """
        Initialize MultiObjectTracker.
        
        Args:
            max_age: Maximum frames to keep a track without updates
            min_hits: Minimum hits to confirm a track
            iou_threshold: IoU threshold for matching
            high_det_thresh: High confidence threshold
            low_det_thresh: Low confidence threshold for recovery
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.high_det_thresh = high_det_thresh
        self.low_det_thresh = low_det_thresh
        self.min_motion_pixels = min_motion_pixels
        
        self.tracks: Dict[int, Track] = {}
        self.next_track_id = 1
        self.frame_count = 0
        
        logger.info(
            f"MultiObjectTracker init: max_age={max_age}, min_hits={min_hits}, "
            f"iou_threshold={iou_threshold}, high_det_thresh={high_det_thresh}"
        )
    
    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """
        Update tracks with new detections.
        
        Args:
            detections: List of detection dicts with 'bbox' and 'confidence'
            
        Returns:
            List of confirmed Track objects
        """
        self.frame_count += 1
        
        if not detections:
            detections = []
        
        # Separate high and low confidence detections
        high_conf_dets = [d for d in detections if d["confidence"] >= self.high_det_thresh]
        low_conf_dets = [d for d in detections if d["confidence"] < self.high_det_thresh]
        
        # Match high confidence detections
        matched_pairs, unmatched_dets, unmatched_tracks = self._match_detections(
            high_conf_dets,
            list(self.tracks.values())
        )
        
        # Update matched tracks
        for track_idx, det_idx in matched_pairs:
            track = list(self.tracks.values())[track_idx]
            det = high_conf_dets[det_idx]
            
            self._update_track(track, det)
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            det = high_conf_dets[det_idx]
            self._create_track(det)
        
        # Mark unmatched tracks as inactive
        for track_idx in unmatched_tracks:
            track = list(self.tracks.values())[track_idx]
            track.time_since_update += 1
        
        # Try to recover tracks with low confidence detections
        if low_conf_dets:
            self._recover_tracks(low_conf_dets)
        
        # Remove aged-out tracks
        self._prune_tracks()
        
        # Return confirmed tracks
        confirmed_tracks = [
            t for t in self.tracks.values()
            if t.state == "confirmed"
        ]
        
        logger.debug(
            f"Frame {self.frame_count}: {len(high_conf_dets)} detections, "
            f"{len(confirmed_tracks)} confirmed tracks"
        )
        
        return confirmed_tracks
    
    def _match_detections(
        self,
        detections: List[Dict[str, Any]],
        tracks: List[Track]
    ) -> tuple:
        """
        Match detections to tracks using IoU.
        
        Returns:
            (matched_pairs, unmatched_dets, unmatched_tracks)
        """
        if not detections or not tracks:
            return [], list(range(len(detections))), list(range(len(tracks)))
        
        # Compute IoU matrix
        iou_matrix = self._compute_iou_matrix(detections, tracks)
        
        # Hungarian algorithm (simplified greedy matching)
        matched_pairs = []
        matched_dets = set()
        matched_tracks = set()
        
        # Sort by IoU (descending)
        matches = []
        for det_idx in range(len(detections)):
            for track_idx in range(len(tracks)):
                if iou_matrix[det_idx, track_idx] > self.iou_threshold:
                    matches.append((
                        iou_matrix[det_idx, track_idx],
                        det_idx,
                        track_idx
                    ))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        
        # Greedy matching
        for _, det_idx, track_idx in matches:
            if det_idx not in matched_dets and track_idx not in matched_tracks:
                matched_pairs.append((track_idx, det_idx))
                matched_dets.add(det_idx)
                matched_tracks.add(track_idx)
        
        unmatched_dets = [i for i in range(len(detections)) if i not in matched_dets]
        unmatched_tracks = [i for i in range(len(tracks)) if i not in matched_tracks]
        
        return matched_pairs, unmatched_dets, unmatched_tracks
    
    def _compute_iou_matrix(
        self,
        detections: List[Dict[str, Any]],
        tracks: List[Track]
    ) -> np.ndarray:
        """Compute IoU matrix between detections and tracks."""
        n_dets = len(detections)
        n_tracks = len(tracks)
        
        iou_matrix = np.zeros((n_dets, n_tracks))
        
        for det_idx, det in enumerate(detections):
            det_box = det["bbox"]
            
            for track_idx, track in enumerate(tracks):
                track_box = track.bbox
                
                iou = self._compute_iou(det_box, track_box)
                iou_matrix[det_idx, track_idx] = iou
        
        return iou_matrix
    
    @staticmethod
    def _compute_iou(box1: List[float], box2: List[float]) -> float:
        """Compute Intersection over Union (IoU) for two boxes."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Intersection
        inter_xmin = max(x1_min, x2_min)
        inter_ymin = max(y1_min, y2_min)
        inter_xmax = min(x1_max, x2_max)
        inter_ymax = min(y1_max, y2_max)
        
        if inter_xmax < inter_xmin or inter_ymax < inter_ymin:
            return 0.0
        
        inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
        
        # Union
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0.0
        
        return inter_area / union_area
    
    def _update_track(self, track: Track, detection: Dict[str, Any]) -> None:
        """Update a track with a new detection."""
        track.bbox = detection["bbox"]
        track.confidence = detection["confidence"]
        track.hits += 1
        track.time_since_update = 0
        track.age += 1
        
        # Confirm track after min_hits + minimum motion (reject static blur patches)
        if track.hits >= self.min_hits and self._has_minimum_motion(track):
            track.state = "confirmed"
        
        # Add to trajectory
        track.trajectory.append((self.frame_count, track.bbox))

    def _has_minimum_motion(self, track: Track) -> bool:
        """Real people move; anonymised blur blocks stay fixed."""
        if len(track.trajectory) < 2:
            return track.hits >= self.min_hits + 1
        _, b0 = track.trajectory[0]
        _, b1 = track.trajectory[-1]
        c0x, c0y = (b0[0] + b0[2]) / 2, (b0[1] + b0[3]) / 2
        c1x, c1y = (b1[0] + b1[2]) / 2, (b1[1] + b1[3]) / 2
        dist = ((c1x - c0x) ** 2 + (c1y - c0y) ** 2) ** 0.5
        return dist >= self.min_motion_pixels
    
    def _create_track(self, detection: Dict[str, Any]) -> None:
        """Create a new track."""
        track = Track(
            track_id=self.next_track_id,
            bbox=detection["bbox"],
            confidence=detection["confidence"],
            age=1,
            hits=1
        )
        self.tracks[self.next_track_id] = track
        self.next_track_id += 1
    
    def _recover_tracks(self, detections: List[Dict[str, Any]]) -> None:
        """Try to recover deleted or unconfirmed tracks."""
        for det in detections:
            best_track_id = None
            best_iou = 0
            
            for track_id, track in self.tracks.items():
                if track.state == "deleted" and track.time_since_update < self.max_age:
                    iou = self._compute_iou(det["bbox"], track.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_track_id = track_id
            
            if best_track_id is not None and best_iou > 0.1:
                track = self.tracks[best_track_id]
                self._update_track(track, det)
                track.state = "confirmed"
    
    def _prune_tracks(self) -> None:
        """Remove aged-out tracks."""
        to_delete = []
        
        for track_id, track in self.tracks.items():
            if track.time_since_update > self.max_age:
                track.state = "deleted"
                to_delete.append(track_id)
        
        for track_id in to_delete:
            del self.tracks[track_id]
    
    def get_active_tracks(self) -> List[Track]:
        """Get all active (confirmed) tracks."""
        return [
            t for t in self.tracks.values()
            if t.state == "confirmed"
        ]
    
    def get_all_tracks(self) -> List[Track]:
        """Get all tracks (confirmed and tentative)."""
        return [
            t for t in self.tracks.values()
            if t.state != "deleted"
        ]
    
    def get_track(self, track_id: int) -> Optional[Track]:
        """Get a specific track by ID."""
        return self.tracks.get(track_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        confirmed = [t for t in self.tracks.values() if t.state == "confirmed"]
        tentative = [t for t in self.tracks.values() if t.state == "tentative"]
        
        return {
            "frame_count": self.frame_count,
            "total_tracks_created": self.next_track_id - 1,
            "active_confirmed": len(confirmed),
            "active_tentative": len(tentative),
            "max_track_id": self.next_track_id - 1
        }


def create_tracker(
    max_age: int = 30,
    min_hits: int = 3,
    high_det_thresh: float = 0.5,
    low_det_thresh: float = 0.1,
    min_motion_pixels: float = 12.0,
) -> MultiObjectTracker:
    """
    Factory function to create MultiObjectTracker.
    
    Args:
        max_age: Max frames to keep track alive
        min_hits: Min detections to confirm track
        high_det_thresh: High confidence threshold for primary detections
        low_det_thresh: Low confidence threshold for recovery
        
    Returns:
        Configured MultiObjectTracker instance
    """
    return MultiObjectTracker(
        max_age=max_age,
        min_hits=min_hits,
        high_det_thresh=high_det_thresh,
        low_det_thresh=low_det_thresh,
        min_motion_pixels=min_motion_pixels,
    )
