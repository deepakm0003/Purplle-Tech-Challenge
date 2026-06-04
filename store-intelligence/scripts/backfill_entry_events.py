#!/usr/bin/env python3
"""Add ENTRY events to JSONL files that only contain ZONE_DWELL on entry cameras."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.schemas import Event  # noqa: E402
from api.services.store_catalog import bootstrap_events_dir, get_store, list_stores  # noqa: E402
from detector.entry_backfill import (  # noqa: E402
    entry_camera_ids_for_store,
    supplement_entry_events,
)


def _rewrite(path: Path, store_id: str) -> int:
    if not path.is_file():
        return 0
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    events = [Event(**json.loads(ln)) for ln in lines]
    before = sum(1 for e in events if e.event_type.value == "ENTRY")
    entry_cams = entry_camera_ids_for_store(store_id)
    updated = supplement_entry_events(events, entry_camera_ids=entry_cams)
    after = sum(1 for e in updated if e.event_type.value == "ENTRY")
    if after <= before:
        return 0
    with path.open("w", encoding="utf-8") as f:
        for e in updated:
            f.write(json.dumps(e.model_dump(mode="json"), default=str) + "\n")
    return after - before


def _paths_for_store(store) -> list[Path]:
    paths: list[Path] = []
    if store.events_dir.is_dir():
        paths.extend(store.events_dir.glob("*.jsonl"))
    boot = bootstrap_events_dir(store)
    if boot.is_dir():
        paths.extend(boot.glob("*.jsonl"))
    return paths


def main() -> int:
    total = 0
    for store in list_stores():
        if not get_store(store.id):
            continue
        print(f"\n{store.name} ({store.id})")
        for path in _paths_for_store(store):
            added = _rewrite(path, store.id)
            if added:
                print(f"  +{added} ENTRY in {path.name}")
                total += added
    print(f"\nAdded {total} ENTRY rows. Restart API: uvicorn api.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
