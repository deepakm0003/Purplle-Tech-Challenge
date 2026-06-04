"""
File-backed event store for CCTV pipeline output (JSONL).

Loads events from output/events/*.jsonl and supports idempotent append on ingest.
Works without Postgres seed data — required for take-home acceptance gate.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from api.schemas import Event

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_DIR = PROJECT_ROOT / "output" / "events"


class JsonlEventStore:
    """In-memory index + JSONL persistence for pipeline events."""

    def __init__(self, events_dir: Optional[Path] = None):
        self.events_dir = Path(events_dir or DEFAULT_EVENTS_DIR)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._by_store: Dict[str, List[Event]] = defaultdict(list)
        self._seen_ids: Set[str] = set()
        self._loaded = False

    def _ingest_file(self, path: Path) -> int:
        added = 0
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return 0

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                event = Event(**raw)
            except Exception as exc:
                logger.debug("Skip invalid line in %s: %s", path.name, exc)
                continue

            if event.event_id in self._seen_ids:
                continue
            self._seen_ids.add(event.event_id)
            self._by_store[event.store_id].append(event)
            added += 1
        return added

    def load_from_disk(self, force: bool = False) -> int:
        """Load all *.jsonl under events_dir and per-store output folders."""
        if self._loaded and not force:
            return sum(len(v) for v in self._by_store.values())

        total = 0
        if self.events_dir.is_dir():
            for path in sorted(self.events_dir.glob("*.jsonl")):
                total += self._ingest_file(path)

        output_root = PROJECT_ROOT / "output"
        if output_root.is_dir():
            for path in sorted(output_root.glob("store-*/events/*.jsonl")):
                total += self._ingest_file(path)

        self._loaded = True
        logger.info("JsonlEventStore: loaded %s events from disk", total)
        return total

    def load_events_for_store(self, store_id: str) -> List[Event]:
        if not self._loaded:
            self.load_from_disk()
        return list(self._by_store.get(store_id, []))

    def append(self, event: Event) -> bool:
        """Append event if new; persist to ingested.jsonl."""
        if event.event_id in self._seen_ids:
            return False

        self._seen_ids.add(event.event_id)
        self._by_store[event.store_id].append(event)

        ingest_path = self.events_dir / f"{event.store_id}_ingested.jsonl"
        with ingest_path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return True

    def event_count(self, store_id: str) -> int:
        return len(self.load_events_for_store(store_id))


_store: Optional[JsonlEventStore] = None


def get_jsonl_event_store() -> JsonlEventStore:
    global _store
    if _store is None:
        _store = JsonlEventStore()
    return _store

