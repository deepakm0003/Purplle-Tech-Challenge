"""
Export internal Event objects to Purplle sample_events JSONL format (submission).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

from api.schemas import Event, EventType


def _store_code(store_id: str) -> str:
    digits = "".join(c for c in store_id if c.isdigit())
    return f"store_{digits or store_id.lower()}"


def event_to_sample_record(event: Event) -> dict:
    """Map challenge Event → sample_eventsbe42122.jsonl shape."""
    ts = event.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")

    if event.event_type in (EventType.ENTRY, EventType.EXIT, EventType.REENTRY):
        et = event.event_type.value.lower()
        if et == "reentry":
            et = "entry"
        return {
            "event_type": et,
            "id_token": event.visitor_id,
            "store_code": _store_code(event.store_id),
            "camera_id": event.camera_id.lower().replace("-", ""),
            "event_timestamp": ts,
            "is_staff": event.is_staff,
            "gender_pred": None,
            "age_pred": None,
            "age_bucket": None,
            "is_face_hidden": True,
            "group_id": None,
            "group_size": None,
        }

    if event.event_type in (EventType.ZONE_ENTER, EventType.ZONE_EXIT, EventType.ZONE_DWELL):
        et = "zone_entered" if event.event_type == EventType.ZONE_ENTER else "zone_exited"
        if event.event_type == EventType.ZONE_DWELL:
            et = "zone_entered"
        track_num = 0
        if event.visitor_id.startswith("VIS_"):
            tail = event.visitor_id.split("_")[-1]
            if tail.isdigit():
                track_num = int(tail)
        cx, cy = 400.0, 300.0
        return {
            "event_type": et,
            "track_id": track_num or hash(event.visitor_id) % 10000,
            "store_id": event.store_id,
            "camera_id": event.camera_id,
            "zone_id": event.zone_id or "UNKNOWN",
            "zone_name": (event.zone_id or "Zone").replace("_", " "),
            "zone_type": "SHELF",
            "is_revenue_zone": "Yes",
            "event_time": ts,
            "zone_hotspot_x": cx,
            "zone_hotspot_y": cy,
            "gender": None,
            "age": None,
            "age_bucket": None,
        }

    if event.event_type in (EventType.BILLING_QUEUE_JOIN, EventType.BILLING_QUEUE_ABANDON):
        abandoned = event.event_type == EventType.BILLING_QUEUE_ABANDON
        return {
            "queue_event_id": str(uuid.uuid4()),
            "event_type": "queue_abandoned" if abandoned else "queue_completed",
            "track_id": hash(event.visitor_id) % 10000,
            "store_id": event.store_id,
            "camera_id": event.camera_id,
            "zone_id": event.zone_id or "BILLING",
            "zone_name": "Billing Counter Queue",
            "zone_type": "BILLING",
            "is_revenue_zone": "Yes",
            "queue_join_ts": ts,
            "queue_served_ts": None if abandoned else ts,
            "queue_exit_ts": ts,
            "wait_seconds": max(0, event.dwell_ms // 1000),
            "queue_position_at_join": event.metadata.queue_depth or 1,
            "abandoned": abandoned,
            "zone_hotspot_x": 600.0,
            "zone_hotspot_y": 180.0,
            "gender": None,
            "age": None,
            "age_bucket": None,
        }

    return event.to_dict()


def write_sample_jsonl(events: Iterable[Event], path: str | Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event_to_sample_record(event), default=str) + "\n")
            count += 1
    return count
