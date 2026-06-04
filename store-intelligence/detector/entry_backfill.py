"""
Derive ENTRY (and optional EXIT) events when pipeline output only has zone/dwell events.

Older runs or high min_hits settings can produce ZONE_DWELL on entry cameras without
separate ENTRY rows — metrics and funnel then show zero visitors.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable

from api.schemas import Event, EventMetadata, EventType


def entry_camera_ids_for_store(store_id: str) -> set[str]:
    from api.services.store_catalog import get_store

    store = get_store(store_id)
    if not store:
        return set()
    return {c.id for c in store.cameras if c.role == "entry"}


def supplement_entry_events(
    events: list[Event],
    *,
    entry_camera_ids: Iterable[str] | None = None,
    add_exit: bool = False,
) -> list[Event]:
    """
    Insert synthetic ENTRY for each visitor whose first event on an entry camera
    is not already ENTRY. Returns a new list (original + supplements).
    """
    if not events:
        return events

    entry_cams = set(entry_camera_ids or [])
    if not entry_cams:
        entry_cams = {
            e.camera_id
            for e in events
            if e.camera_id and (e.zone_id or "").upper() == "ENTRY"
        }

    if not entry_cams:
        return events

    sorted_events = sorted(events, key=lambda e: e.timestamp)
    has_entry: set[str] = {
        e.visitor_id
        for e in sorted_events
        if e.event_type == EventType.ENTRY and e.camera_id in entry_cams
    }

    supplements: list[Event] = []
    first_on_entry: dict[str, Event] = {}
    last_on_entry: dict[str, Event] = {}

    for event in sorted_events:
        if event.camera_id not in entry_cams or event.is_staff:
            continue
        vid = event.visitor_id
        if vid not in first_on_entry:
            first_on_entry[vid] = event
        last_on_entry[vid] = event

    for visitor_id, first in first_on_entry.items():
        if visitor_id in has_entry:
            continue
        supplements.append(
            Event(
                event_id=str(uuid.uuid4()),
                store_id=first.store_id,
                camera_id=first.camera_id,
                visitor_id=visitor_id,
                event_type=EventType.ENTRY,
                timestamp=first.timestamp,
                zone_id=first.zone_id or "ENTRY",
                dwell_ms=0,
                is_staff=first.is_staff,
                confidence=first.confidence,
                metadata=EventMetadata(session_seq=1),
            )
        )

    if add_exit:
        has_exit = {
            e.visitor_id
            for e in sorted_events
            if e.event_type == EventType.EXIT and e.camera_id in entry_cams
        }
        for visitor_id, last in last_on_entry.items():
            if visitor_id in has_exit or visitor_id not in first_on_entry:
                continue
            first = first_on_entry[visitor_id]
            dwell_ms = max(
                0,
                int((last.timestamp - first.timestamp).total_seconds() * 1000),
            )
            supplements.append(
                Event(
                    event_id=str(uuid.uuid4()),
                    store_id=last.store_id,
                    camera_id=last.camera_id,
                    visitor_id=visitor_id,
                    event_type=EventType.EXIT,
                    timestamp=last.timestamp,
                    zone_id=None,
                    dwell_ms=dwell_ms,
                    is_staff=last.is_staff,
                    confidence=last.confidence,
                    metadata=EventMetadata(session_seq=2),
                )
            )

    if not supplements:
        return events

    merged = sorted(events + supplements, key=lambda e: e.timestamp)
    return merged
