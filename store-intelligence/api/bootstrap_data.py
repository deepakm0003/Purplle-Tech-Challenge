"""
Bootstrap analytics from sample_events JSONL, pipeline output, and POS CSV.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from api.schemas import Event
from api.routes.analytics import get_analytics_service
from detector.entry_backfill import entry_camera_ids_for_store, supplement_entry_events
from api.services.store_catalog import (
    iter_event_jsonl_paths,
    list_stores,
    pos_csv_path,
    sample_events_path,
    sample_events_store_map,
)

logger = logging.getLogger(__name__)


def _load_sample_events(target_store_id: str) -> list[Event]:
    path = sample_events_path()
    if not path.is_file():
        return []

    store_map = sample_events_store_map()
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            mapped = store_map.get(str(raw.get("store_code", "")), None)
            if mapped is None:
                mapped = store_map.get(str(raw.get("store_id", "")), None)
            if mapped and mapped != target_store_id:
                continue
            if mapped:
                raw = dict(raw)
                raw["store_id"] = mapped
            event = Event(**raw)
            if event.store_id == target_store_id:
                events.append(event)
        except Exception as exc:
            logger.debug("Skip sample event line: %s", exc)
    return events


def _load_pipeline_events(store_id: str) -> list[Event]:
    from api.services.store_catalog import get_store

    store = get_store(store_id)
    if not store:
        return []

    events: list[Event] = []
    seen: set[str] = set()
    for path in iter_event_jsonl_paths(store):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = Event(**json.loads(line))
            except Exception:
                continue
            if event.store_id != store_id:
                continue
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            events.append(event)

    entry_cams = entry_camera_ids_for_store(store_id)
    if entry_cams:
        events = supplement_entry_events(events, entry_camera_ids=entry_cams)
    return events


def bootstrap_store(store_id: str) -> int:
    """Load events + POS into analytics service. Returns event count."""
    from api.services.store_catalog import get_store

    store = get_store(store_id)
    sample = _load_sample_events(store_id)
    pipeline = _load_pipeline_events(store_id)

    merged: dict[str, Event] = {}
    for e in sample + pipeline:
        merged[e.event_id] = e
    events = list(merged.values())

    svc = get_analytics_service(store_id)
    svc.ingest_events(events, replace=True)

    pos_path = pos_csv_path()
    if pos_path.is_file():
        svc.load_pos_data(str(pos_path))
        svc._pos_loaded = True
        if store and hasattr(svc.pos_processor, "transactions"):
            allowed = set(store.pos_store_ids)
            svc.pos_processor.transactions = [
                t for t in svc.pos_processor.transactions if t.store_id in allowed
            ]

    logger.info(
        "Bootstrap %s: %s events (%s sample + %s pipeline), POS txns=%s",
        store_id,
        len(events),
        len(sample),
        len(pipeline),
        len(getattr(svc.pos_processor, "transactions", [])),
    )
    return len(events)


def bootstrap_all_stores() -> None:
    for store in list_stores():
        try:
            bootstrap_store(store.id)
        except Exception as exc:
            logger.warning("Bootstrap failed for %s: %s", store.id, exc)
