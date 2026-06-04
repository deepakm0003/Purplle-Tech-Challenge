"""
Generate annotated CCTV previews (bounding boxes + zone labels) for dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from detector.detector import create_detector
from detector.tracker import create_tracker
from detector.zone_mapper import ZoneMapper


def _draw_zones(frame: np.ndarray, zone_mapper: ZoneMapper, alpha: float = 0.2) -> None:
    overlay = frame.copy()
    for zone_id, polygon in zone_mapper.zones.items():
        pts = np.array(polygon, dtype=np.int32)
        color = (80, 180, 255) if zone_id == "CHECKOUT" else (100, 255, 100)
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 2)
        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))
        cv2.putText(frame, zone_id, (cx - 40, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _draw_tracks(
    frame: np.ndarray,
    tracks: list,
    track_to_label: dict,
) -> None:
    for track in tracks:
        x1, y1, x2, y2 = [int(c) for c in track.bbox]
        label = track_to_label.get(track.track_id, f"T{track.track_id}")
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"{label} {track.confidence:.2f}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
        )


def generate_preview(
    video_path: str,
    output_jpg: str,
    layout_path: str = "config/zones.json",
    confidence: float = 0.3,
    frame_index: Optional[int] = None,
) -> bool:
    """Save one annotated frame with person boxes and zones."""
    video_path = Path(video_path)
    out = Path(output_jpg)
    out.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    idx = frame_index if frame_index is not None else total // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
    cap.release()
    if not ret:
        return False

    h, w = frame.shape[:2]
    detector = create_detector(confidence_threshold=confidence)
    tracker = create_tracker(min_hits=1, high_det_thresh=0.25)
    zone_mapper = ZoneMapper(layout_path) if Path(layout_path).exists() else None
    if zone_mapper:
        sx, sy = w / 800, h / 600
        zone_mapper.zones = {
            zid: [(x * sx, y * sy) for x, y in poly]
            for zid, poly in zone_mapper.zones.items()
        }
        _draw_zones(frame, zone_mapper)

    detections = detector.detect(frame)
    det_list = [{"bbox": d.bbox, "confidence": d.confidence} for d in detections]
    tracks = tracker.update(det_list)
    labels = {t.track_id: f"P{t.track_id}" for t in tracks}
    _draw_tracks(frame, tracks, labels)

    cv2.putText(
        frame,
        f"{video_path.name} | {len(tracks)} people detected",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    cv2.imwrite(str(out), frame)
    return True


def generate_annotated_clip(
    video_path: str,
    output_mp4: str,
    layout_path: str = "config/zones.json",
    sample_rate: int = 15,
    max_frames: int = 120,
    confidence: float = 0.3,
) -> bool:
    """Write a short MP4 with boxes (sampled frames) for dashboard demo."""
    video_path = Path(video_path)
    out = Path(output_mp4)
    out.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    out_fps = max(2, fps / sample_rate)

    detector = create_detector(confidence_threshold=confidence)
    tracker = create_tracker(min_hits=1, high_det_thresh=0.25)
    zone_mapper = ZoneMapper(layout_path) if Path(layout_path).exists() else None
    if zone_mapper:
        sx, sy = w / 800, h / 600
        zone_mapper.zones = {
            zid: [(x * sx, y * sy) for x, y in poly]
            for zid, poly in zone_mapper.zones.items()
        }

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out), fourcc, out_fps, (w, h))

    frame_i = 0
    written = 0
    while written < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_i += 1
        if frame_i % sample_rate != 0:
            continue

        vis = frame.copy()
        if zone_mapper:
            _draw_zones(vis, zone_mapper)
        detections = detector.detect(frame)
        tracks = tracker.update(
            [{"bbox": d.bbox, "confidence": d.confidence} for d in detections]
        )
        _draw_tracks(vis, tracks, {t.track_id: f"P{t.track_id}" for t in tracks})
        writer.write(vis)
        written += 1

    cap.release()
    writer.release()
    return written > 0
