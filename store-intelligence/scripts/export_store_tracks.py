#!/usr/bin/env python3
"""
Export per-frame bbox JSON for Store 1 / Store 2 (live CCTV overlay).

Uses same robust detection settings as process_stores.py.

Usage:
  python scripts/export_store_tracks.py --store ST1008
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.services.store_catalog import camera_events_path, camera_tracks_path, list_stores  # noqa: E402
from scripts.process_stores import LAYOUT_FOR_STORE, entry_camera_ids  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export tracking JSON for dashboard overlay")
    parser.add_argument("--store", help="Store id filter")
    parser.add_argument("--sample-rate", type=int, default=3)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--min-hits", type=int, default=4)
    parser.add_argument("--model", default="nano")
    args = parser.parse_args()

    stores = list_stores()
    if args.store:
        stores = [s for s in stores if s.id == args.store]

    for store in stores:
        store.tracks_dir.mkdir(parents=True, exist_ok=True)
        layout = LAYOUT_FOR_STORE.get(store.id, "config/zones.json")
        entries = entry_camera_ids(store)
        print(f"\n=== {store.name} ===")
        for idx, cam in enumerate(store.cameras, start=1):
            video = store.root / cam.file
            if not video.is_file():
                continue
            tracks_file = camera_tracks_path(store, cam)
            events_file = camera_events_path(store, cam)
            events_file.parent.mkdir(parents=True, exist_ok=True)

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
                store.id,
                "--camera-id",
                cam.id,
                "--camera-role",
                cam.role,
                "--layout",
                layout,
                "--sample-rate",
                str(args.sample_rate),
                "--confidence",
                str(args.confidence),
                "--min-hits",
                str(args.min_hits),
                "--model",
                args.model,
            ]
            for eid in entries:
                cmd.extend(["--entry-camera-id", eid])

            print(f"[{idx}] {cam.file} → {tracks_file.relative_to(ROOT)}")
            if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
                return 1

    print("\nDone. Refresh CCTV page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
