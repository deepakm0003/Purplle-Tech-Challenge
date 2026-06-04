#!/usr/bin/env python3
"""
Merge pipeline JSONL from all stores → submission deliverables.

Outputs:
  output/submission_events.jsonl       — challenge Event schema (API-compatible)
  output/sample_format_events.jsonl    — sample_eventsbe42122.jsonl shape

Usage:
  python scripts/build_submission_events.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.schemas import Event  # noqa: E402
from api.services.store_catalog import iter_event_jsonl_paths, list_stores  # noqa: E402
from detector.event_postprocess import merge_store_events, postprocess_events  # noqa: E402
from detector.sample_format_export import write_sample_jsonl  # noqa: E402


def load_store_events(store_id: str) -> list[Event]:
    from api.services.store_catalog import get_store

    store = get_store(store_id)
    if not store:
        return []
    entry_ids = {c.id for c in store.cameras if c.role == "entry"}
    events: list[Event] = []
    for path in iter_event_jsonl_paths(store):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(Event(**json.loads(line)))
            except Exception:
                continue
    return postprocess_events(events, entry_camera_ids=entry_ids, mark_staff=True)


def main() -> int:
    all_events: list[Event] = []
    for store in list_stores():
        store_events = load_store_events(store.id)
        print(f"{store.name} ({store.id}): {len(store_events)} events")
        all_events.extend(store_events)

    merged = merge_store_events([all_events])
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    challenge_path = out_dir / "submission_events.jsonl"
    with challenge_path.open("w", encoding="utf-8") as f:
        for event in merged:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    sample_path = out_dir / "sample_format_events.jsonl"
    write_sample_jsonl(merged, sample_path)

    print(f"\nWrote {len(merged)} events:")
    print(f"  Challenge schema → {challenge_path}")
    print(f"  Sample schema    → {sample_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
