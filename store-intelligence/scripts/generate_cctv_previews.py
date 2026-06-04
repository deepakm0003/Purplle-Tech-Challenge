#!/usr/bin/env python3
"""Generate annotated preview images + short clips for CCTV dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from detector.preview import generate_annotated_clip, generate_preview  # noqa: E402

CCTV_DIR = ROOT / "CCTV Footage"
OUT_DIR = ROOT / "output" / "previews"
LAYOUT = ROOT / "config" / "zones.json"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    videos = sorted(CCTV_DIR.glob("*.mp4"))
    if not videos:
        print(f"No MP4 files in {CCTV_DIR}")
        return 1

    for video in videos:
        slug = video.stem.replace(" ", "_")
        jpg = OUT_DIR / f"{slug}_preview.jpg"
        mp4 = OUT_DIR / f"{slug}_annotated.mp4"
        print(f"[{video.name}] preview...", end=" ", flush=True)
        ok = generate_preview(str(video), str(jpg), str(LAYOUT))
        print("ok" if ok else "fail")
        print(f"[{video.name}] clip...", end=" ", flush=True)
        ok2 = generate_annotated_clip(
            str(video), str(mp4), str(LAYOUT), sample_rate=20, max_frames=90
        )
        print("ok" if ok2 else "fail")

    print(f"\nDone → {OUT_DIR}")
    print("Restart API to serve /cctv-previews/ and refresh dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
