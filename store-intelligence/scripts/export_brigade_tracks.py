#!/usr/bin/env python3
"""
Export per-frame tracking JSON for all Brigade cameras (frontend live overlay).

Usage:
  python scripts/export_brigade_tracks.py
  python scripts/export_brigade_tracks.py --sample-rate 3 --min-hits 1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CCTV_DIR = ROOT / "CCTV Footage"
TRACKS_DIR = ROOT / "output" / "tracks"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export per-frame bbox JSON for dashboard overlay")
    parser.add_argument("--sample-rate", type=int, default=3, help="YOLO every N frames (3 = smoother)")
    parser.add_argument("--confidence", type=float, default=0.3)
    parser.add_argument("--min-hits", type=int, default=1, help="Confirm tracks quickly for overlay")
    parser.add_argument("--model", default="nano")
    args = parser.parse_args()

    videos = sorted(CCTV_DIR.glob("*.mp4"))
    if not videos:
        print(f"No videos in {CCTV_DIR}")
        return 1

    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Exporting tracks for {len(videos)} videos → {TRACKS_DIR}\n")

    for idx, video in enumerate(videos, start=1):
        slug = video.stem.replace(" ", "_")
        tracks_file = TRACKS_DIR / f"{slug}_tracks.json"
        events_file = ROOT / "output" / "events" / f"{slug}_events.jsonl"
        cmd = [
            sys.executable,
            "-m",
            "detector.process_video",
            "-v",
            str(video),
            "-o",
            str(events_file),
            "--export-tracks",
            "--tracks-output",
            str(tracks_file),
            "--store-id",
            "ST1008",
            "--camera-id",
            f"CAM-{idx}",
            "--sample-rate",
            str(args.sample_rate),
            "--confidence",
            str(args.confidence),
            "--min-hits",
            str(args.min_hits),
            "--model",
            args.model,
        ]
        print(f"[{idx}/{len(videos)}] {video.name} → {tracks_file.name}")
        if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
            return 1

    print("\nDone. Refresh CCTV page — boxes will follow people during playback.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
