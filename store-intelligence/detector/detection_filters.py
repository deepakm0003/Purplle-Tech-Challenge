"""
Heuristic filters to reduce false person detections in anonymised CCTV.

Targets:
- Face-blur / poster patches (small, square-ish, static)
- Mirror reflections (duplicate overlapping boxes)
- Floor / edge artefacts
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

DetectionDict = Dict[str, Any]


def bbox_area(bbox: List[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_center(bbox: List[float]) -> Tuple[float, float]:
    return (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0


def compute_iou(box1: List[float], box2: List[float]) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = bbox_area(box1) + bbox_area(box2) - inter
    return inter / union if union > 0 else 0.0


class DetectionFilter:
    """Configurable geometric + confidence filters per camera role."""

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        camera_role: str = "zone",
        min_confidence: float = 0.42,
    ):
        self.fw = max(frame_width, 1)
        self.fh = max(frame_height, 1)
        self.camera_role = camera_role
        self.min_confidence = min_confidence
        self.frame_area = self.fw * self.fh

    def filter_detections(self, detections: List[DetectionDict]) -> List[DetectionDict]:
        kept: List[DetectionDict] = []
        for det in detections:
            bbox = det.get("bbox") or []
            conf = float(det.get("confidence", 0))
            if len(bbox) != 4:
                continue
            if not self._valid_geometry(bbox, conf):
                continue
            if not self._valid_position(bbox):
                continue
            kept.append(det)

        return self._nms_duplicates(kept, iou_threshold=0.48)

    def _valid_geometry(self, bbox: List[float], confidence: float) -> bool:
        if confidence < self.min_confidence:
            return False

        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= 4 or h <= 8:
            return False

        area_ratio = bbox_area(bbox) / self.frame_area
        # Blur patches / noise — very small or huge
        if area_ratio < 0.0025:
            return False
        if area_ratio > 0.28:
            return False

        aspect = w / max(h, 1.0)
        # Real standing people: taller than wide
        if aspect > 0.78:
            return False
        if aspect < 0.15:
            return False

        height_ratio = h / self.fh
        if height_ratio < 0.07:
            return False
        if height_ratio > 0.92:
            return False

        return True

    def _valid_position(self, bbox: List[float]) -> bool:
        cx, cy = bbox_center(bbox)
        # Floor reflections / counter edge artefacts
        if cy > self.fh * 0.96:
            return False

        if self.camera_role == "entry":
            # Ignore tiny boxes hugging the very top (often signage / blur band)
            if cy < self.fh * 0.04 and bbox_area(bbox) / self.frame_area < 0.01:
                return False

        return True

    @staticmethod
    def _nms_duplicates(
        detections: List[DetectionDict],
        iou_threshold: float = 0.48,
    ) -> List[DetectionDict]:
        """Suppress mirror / duplicate boxes — keep highest confidence + area."""
        if len(detections) <= 1:
            return detections

        ranked = sorted(
            detections,
            key=lambda d: (float(d["confidence"]), bbox_area(d["bbox"])),
            reverse=True,
        )
        kept: List[DetectionDict] = []
        for det in ranked:
            if any(
                compute_iou(det["bbox"], k["bbox"]) > iou_threshold for k in kept
            ):
                continue
            kept.append(det)
        return kept


def dedupe_confirmed_tracks(tracks: list, iou_threshold: float = 0.55) -> list:
    """
    Remove younger duplicate tracks (mirror reflections) keeping the stronger track.
    Expects track objects with .track_id, .bbox, .hits, .confidence.
    """
    if len(tracks) <= 1:
        return tracks

    ranked = sorted(tracks, key=lambda t: (t.hits, t.confidence), reverse=True)
    kept = []
    for track in ranked:
        if any(
            compute_iou(track.bbox, k.bbox) > iou_threshold for k in kept
        ):
            continue
        kept.append(track)
    return kept
