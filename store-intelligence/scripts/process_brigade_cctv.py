#!/usr/bin/env python3
"""
Process all five Brigade Bangalore CCTV files (CAM 1–5.mp4).

Usage (from store-intelligence folder):
  python scripts/process_brigade_cctv.py
  python scripts/process_brigade_cctv.py --sample-rate 15   # faster, fewer frames
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CCTV_DIR = ROOT / "CCTV Footage"
OUT_DIR = ROOT / "output" / "events"


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-process Brigade CCTV MP4 files")
    parser.add_argument("--sample-rate", type=int, default=5, help="Frame skip (default 5)")
    parser.add_argument("--confidence", type=float, default=0.3, help="Detection confidence")
    parser.add_argument("--min-hits", type=int, default=2, help="Tracker min hits")
    parser.add_argument("--model", default="nano", help="YOLO size: nano|small|medium")
    parser.add_argument(
        "--export-tracks",
        action="store_true",
        help="Also write output/tracks/*_tracks.json for live video overlay",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()

    if not CCTV_DIR.is_dir():
        print(f"CCTV folder not found: {CCTV_DIR}")
        return 1

    videos = sorted(CCTV_DIR.glob("*.mp4"))
    if not videos:
        print(f"No MP4 files in {CCTV_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(videos)} videos → {OUT_DIR}\n")

    for idx, video in enumerate(videos, start=1):
        camera_id = f"CAM-{idx}"
        slug = video.stem.replace(" ", "_")
        out_file = OUT_DIR / f"{slug}_events.jsonl"
        tracks_file = ROOT / "output" / "tracks" / f"{slug}_tracks.json"
        cmd = [
            sys.executable,
            "-m",
            "detector.process_video",
            "-v",
            str(video),
            "-o",
            str(out_file),
            "--store-id",
            "ST1008",
            "--camera-id",
            camera_id,
            "--sample-rate",
            str(args.sample_rate),
            "--confidence",
            str(args.confidence),
            "--min-hits",
            str(args.min_hits),
            "--model",
            args.model,
        ]
        if args.export_tracks:
            tracks_file.parent.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--export-tracks", "--tracks-output", str(tracks_file)])
        print(f"[{idx}/{len(videos)}] {video.name} → {out_file.name}")
        if args.dry_run:
            print("  ", " ".join(f'"{c}"' if " " in c else c for c in cmd))
            continue
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode != 0:
            print(f"Failed on {video.name} (exit {result.returncode})")
            return result.returncode

    print("\nAll videos processed. Event files are in output/events/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
