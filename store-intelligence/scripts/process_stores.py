#!/usr/bin/env python3
"""
Process Store 1 and Store 2 CCTV clips → per-store JSONL events.

Robust defaults (v2):
  confidence 0.45, min-hits 5, sample-rate 5
  ENTRY/EXIT only on entry-role cameras
  Detection filters for blur patches + mirror duplicates

Usage (from store-intelligence/):
  python scripts/process_stores.py
  python scripts/process_stores.py --store ST2002 --export-tracks
  python scripts/build_submission_events.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.services.store_catalog import camera_events_path, get_store, list_stores  # noqa: E402

LAYOUT_FOR_STORE = {
    "ST1008": "config/zones.json",
    "ST2002": "config/store-2-zones.json",
}


def entry_camera_ids(store) -> list[str]:
    return [c.id for c in store.cameras if c.role == "entry"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-process Store 1 / Store 2 CCTV")
    parser.add_argument("--store", help="Store id (e.g. ST1008). Default: all stores")
    parser.add_argument("--sample-rate", type=int, default=5)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--min-hits", type=int, default=5)
    parser.add_argument("--model", default="nano")
    parser.add_argument("--export-tracks", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stores = list_stores()
    if args.store:
        stores = [s for s in stores if s.id == args.store]
        if not stores:
            print(f"Unknown store: {args.store}")
            return 1

    for store in stores:
        if not store.root.is_dir():
            print(f"Missing folder: {store.root}")
            return 1

        layout = LAYOUT_FOR_STORE.get(store.id, "config/zones.json")
        entries = entry_camera_ids(store)

        print(f"\n=== {store.name} ({store.id}) ===")
        print(f"  Layout: {layout} | Entry cameras: {', '.join(entries)}")

        for idx, cam in enumerate(store.cameras, start=1):
            video = store.root / cam.file
            if not video.is_file():
                print(f"  Skip missing: {cam.file}")
                continue

            out_file = camera_events_path(store, cam)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            tracks_file = store.tracks_dir / f"{Path(cam.file).stem.replace(' ', '_')}_tracks.json"

            cmd = [
                sys.executable,
                "-m",
                "detector.process_video",
                "-v",
                str(video),
                "-o",
                str(out_file),
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

            if args.export_tracks:
                store.tracks_dir.mkdir(parents=True, exist_ok=True)
                cmd.extend(["--export-tracks", "--tracks-output", str(tracks_file)])

            print(f"[{idx}/{len(store.cameras)}] {cam.label} ({cam.role}) → {out_file.name}")
            if args.dry_run:
                print("  ", " ".join(cmd))
                continue
            if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
                return 1

    print("\nDone. Run: python scripts/build_submission_events.py")
    print("Then restart API to refresh metrics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
