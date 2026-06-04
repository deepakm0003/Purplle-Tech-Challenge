"""
Multi-store POS + CCTV service (Store 1 / Store 2).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from api.schemas import Event, EventType
from api.services.store_catalog import (
    PROJECT_ROOT,
    camera_events_path,
    camera_tracks_url,
    get_store,
    list_stores,
    pos_csv_path,
)

logger = logging.getLogger(__name__)


def _file_slug(name: str) -> str:
    return Path(name).stem.replace(" ", "_")


@lru_cache(maxsize=1)
def _load_pos_dataframe() -> pd.DataFrame:
    path = pos_csv_path()
    if not path.is_file():
        raise FileNotFoundError(f"POS CSV not found: {path}")

    df = pd.read_csv(path)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
    df["timestamp"] = pd.to_datetime(
        df["order_date"].astype(str) + " " + df["order_time"].astype(str),
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )
    return df


def reload_pos_cache() -> None:
    _load_pos_dataframe.cache_clear()


def _pos_for_store(store_id: str) -> pd.DataFrame:
    store = get_store(store_id)
    if not store:
        return pd.DataFrame()
    df = _load_pos_dataframe()
    return df[df["store_id"].isin(store.pos_store_ids)].copy()


def get_dashboard(store_id: str) -> dict[str, Any]:
    store = get_store(store_id)
    if not store:
        raise ValueError(f"Unknown store: {store_id}")

    df = _pos_for_store(store_id)
    if df.empty:
        return {
            "source": str(pos_csv_path().name),
            "store_name": store.name,
            "store_id": store.id,
            "date": "No POS rows for this store",
            "summary": {
                "total_revenue": 0.0,
                "total_orders": 0,
                "line_items": 0,
                "unique_customers": 0,
                "average_order_value": 0.0,
                "average_items_per_order": 0.0,
            },
            "hourly_revenue": [],
            "top_products": [],
            "top_brands": [],
            "top_categories": [],
            "top_staff": [],
        }

    order_revenue = df.groupby("order_id")["total_amount"].sum()
    trade_date = (
        df["timestamp"].min().strftime("%d %B %Y")
        if df["timestamp"].notna().any()
        else "—"
    )

    hourly = (
        df.dropna(subset=["timestamp"])
        .groupby(df["timestamp"].dt.hour)["total_amount"]
        .sum()
        .reset_index()
    )
    hourly_revenue = [
        {
            "hour": int(row["timestamp"]),
            "label": f"{int(row['timestamp']):02d}:00",
            "revenue": float(row["total_amount"]),
        }
        for _, row in hourly.iterrows()
    ]
    hourly_revenue.sort(key=lambda x: x["hour"])

    top_products = (
        df.groupby("product_id")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
    )
    top_brands = (
        df.groupby("brand_name")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
    )

    return {
        "source": pos_csv_path().name,
        "store_name": store.name,
        "store_id": store.id,
        "date": trade_date,
        "summary": {
            "total_revenue": float(df["total_amount"].sum()),
            "total_orders": int(df["order_id"].nunique()),
            "line_items": int(len(df)),
            "unique_customers": int(df["order_id"].nunique()),
            "average_order_value": float(order_revenue.mean()) if len(order_revenue) else 0.0,
            "average_items_per_order": float(len(df) / max(df["order_id"].nunique(), 1)),
        },
        "hourly_revenue": hourly_revenue,
        "top_products": [
            {"name": f"SKU {pid}", "revenue": float(rev), "count": 1}
            for pid, rev in top_products.items()
        ],
        "top_brands": [
            {"name": str(name), "revenue": float(rev), "count": 1}
            for name, rev in top_brands.items()
        ],
        "top_categories": [],
        "top_staff": [],
    }


def get_pos_analytics(store_id: str) -> dict[str, Any]:
    dashboard = get_dashboard(store_id)
    summary = dashboard["summary"]
    return {
        "total_revenue": summary["total_revenue"],
        "average_basket_size": summary["average_order_value"],
        "total_transactions": summary["total_orders"],
        "revenue_per_visitor": summary["total_revenue"] / max(summary["unique_customers"], 1),
        "top_products": dashboard["top_products"],
        "top_brands": dashboard["top_brands"],
        "top_hours": dashboard["hourly_revenue"],
        "store_name": dashboard["store_name"],
        "date": dashboard["date"],
        "line_items": summary["line_items"],
    }


def _parse_events_file(path: Path) -> list[Event]:
    events: list[Event] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(Event(**json.loads(line)))
        except Exception:
            continue
    return events


def _camera_stats(store_id: str, camera_id: str, events_path: Path) -> dict[str, int]:
    from detector.entry_backfill import supplement_entry_events
    from api.services.store_catalog import get_store

    events = _parse_events_file(events_path)
    store = get_store(store_id)
    entry_cams = {c.id for c in store.cameras if c.role == "entry"} if store else set()
    if entry_cams and events_path.is_file():
        events = supplement_entry_events(events, entry_camera_ids=entry_cams)

    entries = [
        e
        for e in events
        if e.camera_id == camera_id
        and e.event_type == EventType.ENTRY
        and not e.is_staff
    ]
    unique_visitors = len({e.visitor_id for e in entries})
    if unique_visitors == 0 and store and camera_id in entry_cams:
        unique_visitors = len(
            {e.visitor_id for e in events if e.camera_id == camera_id and not e.is_staff}
        )
    total_events = len([e for e in events if e.camera_id == camera_id])
    return {
        "event_count": total_events,
        "entry_count": len(entries),
        "unique_visitors": unique_visitors,
    }


def list_cameras(store_id: str) -> dict[str, Any]:
    store = get_store(store_id)
    if not store:
        raise ValueError(f"Unknown store: {store_id}")

    cameras_out: list[dict[str, Any]] = []
    for cam in store.cameras:
        video = store.root / cam.file
        if not video.is_file():
            continue

        events_path = camera_events_path(store, cam)
        stats = _camera_stats(store.id, cam.id, events_path)
        pipeline_status = "processed" if stats["entry_count"] > 0 or stats["event_count"] > 0 else "pending_processing"
        if events_path.is_file() and events_path.stat().st_size > 2 and pipeline_status == "pending_processing":
            pipeline_status = "processed"

        size_mb = video.stat().st_size / (1024 * 1024)
        tracks = camera_tracks_url(store, cam)

        cameras_out.append(
            {
                "id": cam.id,
                "name": cam.label,
                "role": cam.role,
                "file_name": cam.file,
                "media_url": store.media_url(cam.file),
                "tracks_url": tracks,
                "layout_image_url": store.layout_url(),
                "size_mb": round(size_mb, 1),
                "status": "footage_available",
                "pipeline_status": pipeline_status,
                "event_count": stats["event_count"],
                "entry_count": stats["entry_count"],
                "visitor_count": stats["unique_visitors"],
                "active_tracks": 0,
                "last_frame_timestamp": None,
            }
        )

    return {
        "store_id": store.id,
        "store_name": store.name,
        "footage_date": "Purplle take-home dataset",
        "layout_image_url": store.layout_url(),
        "cameras": cameras_out,
        "total": len(cameras_out),
        "note": (
            "Run: python scripts/process_stores.py && python scripts/export_store_tracks.py "
            f"— output under output/{store.slug}/"
        ),
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }


def list_stores_summary() -> dict[str, Any]:
    return {
        "stores": [
            {
                "store_id": s.id,
                "name": s.name,
                "slug": s.slug,
                "camera_count": len(s.cameras),
                "layout_image_url": s.layout_url(),
            }
            for s in list_stores()
        ],
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }
