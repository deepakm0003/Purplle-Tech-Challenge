#!/usr/bin/env python3
"""
Copy pipeline JSONL into data/bootstrap/ for git submission (no videos).

Run after process_stores.py:
  python scripts/sync_bootstrap_events.py
  python scripts/backfill_entry_events.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.services.store_catalog import bootstrap_events_dir, list_stores  # noqa: E402


def main() -> int:
    for store in list_stores():
        src = store.events_dir
        dst = bootstrap_events_dir(store)
        if not src.is_dir():
            print(f"Skip {store.id}: no {src}")
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(src.glob("*.jsonl")):
            target = dst / path.name
            shutil.copy2(path, target)
            print(f"  {path.name} -> {target.relative_to(ROOT)}")
    print("\nCommit data/bootstrap/ for reviewers. Videos stay outside git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
