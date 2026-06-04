"""
Export per-frame bounding boxes for frontend video overlay playback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from detector.tracker import Track
from detector.zone_mapper import ZoneMapper


class FrameTrackRecorder:
    """Records track bboxes on every video frame for canvas overlay sync."""

    def __init__(
        self,
        video_name: str,
        fps: float,
        width: int,
        height: int,
        sample_rate: int,
    ):
        self.meta = {
            "version": 1,
            "video": video_name,
            "fps": fps,
            "width": width,
            "height": height,
            "inference_sample_rate": sample_rate,
        }
        self.frames: List[Dict[str, Any]] = []
        self._last_index: Dict[int, int] = {}  # frame_idx -> index in self.frames

    def record(
        self,
        frame_idx: int,
        tracks: List[Track],
        zone_mapper: Optional[ZoneMapper] = None,
    ) -> None:
        """Snapshot confirmed + recent tentative tracks for this frame index (0-based)."""
        objects: List[Dict[str, Any]] = []
        for track in tracks:
            if track.state == "deleted" or not track.bbox:
                continue
            if track.state == "tentative" and track.time_since_update > 0:
                continue
            zone_id = None
            if zone_mapper:
                try:
                    zone_id = zone_mapper.get_zone(track.bbox)
                except Exception:
                    pass
            x1, y1, x2, y2 = track.bbox
            objects.append(
                {
                    "id": track.track_id,
                    "b": [int(x1), int(y1), int(x2), int(y2)],
                    "c": round(float(track.confidence), 3),
                    "z": zone_id,
                }
            )

        entry = {"i": frame_idx, "o": objects}
        if frame_idx in self._last_index:
            self.frames[self._last_index[frame_idx]] = entry
        else:
            self._last_index[frame_idx] = len(self.frames)
            self.frames.append(entry)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**self.meta, "frame_count": len(self.frames), "frames": self.frames}
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        logger.info("Saved %s track frames → %s", len(self.frames), path)
