"""
Post-process pipeline events: staff flags, dedupe, entry-camera-only footfall.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import List

from api.schemas import Event, EventType
from detector.staff_classifier import StaffClassifier

logger = logging.getLogger(__name__)


def postprocess_events(
    events: List[Event],
    *,
    entry_camera_ids: set[str] | None = None,
    mark_staff: bool = True,
) -> List[Event]:
    """Clean and enrich events before persistence."""
    if not events:
        return events

    cleaned: List[Event] = []
    for event in events:
        if entry_camera_ids and event.event_type in (EventType.ENTRY, EventType.EXIT):
            if event.camera_id not in entry_camera_ids:
                continue
        cleaned.append(event)

    if mark_staff:
        classifier = StaffClassifier()
        staff_map = classifier.classify_events(cleaned)
        for event in cleaned:
            info = staff_map.get(event.visitor_id)
            if info and info.get("is_staff"):
                event.is_staff = True

    return _dedupe_entry_reentry(cleaned)


def _dedupe_entry_reentry(events: List[Event]) -> List[Event]:
    """Drop duplicate ENTRY for same visitor within 30s (track fragmentation)."""
    seen: dict[str, float] = {}
    out: List[Event] = []
    for event in sorted(events, key=lambda e: e.timestamp):
        if event.event_type != EventType.ENTRY:
            out.append(event)
            continue
        key = event.visitor_id
        ts = event.timestamp.timestamp()
        last = seen.get(key)
        if last is not None and ts - last < 30:
            continue
        seen[key] = ts
        out.append(event)
    return out


def merge_store_events(event_lists: List[List[Event]]) -> List[Event]:
    merged: dict[str, Event] = {}
    for events in event_lists:
        for e in events:
            merged[e.event_id] = e
    return sorted(merged.values(), key=lambda e: e.timestamp)
