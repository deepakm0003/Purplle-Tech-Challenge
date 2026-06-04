"""
Brigade Bangalore store analytics from Purplle POS CSV (10 April 2026).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from configs import get_settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = PROJECT_ROOT / "Brigade_Bangalore_10_April_26 (1)bc6219c.csv"
DEFAULT_CCTV_DIR = PROJECT_ROOT / "CCTV Footage"


def _csv_path() -> Path:
    settings = get_settings()
    custom = getattr(settings, "brigade_csv_path", None)
    if custom:
        return Path(custom)
    return DEFAULT_CSV


def _cctv_dir() -> Path:
    settings = get_settings()
    custom = getattr(settings, "brigade_cctv_dir", None)
    if custom:
        return Path(custom)
    return DEFAULT_CCTV_DIR


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    path = _csv_path()
    if not path.exists():
        raise FileNotFoundError(f"Brigade CSV not found: {path}")

    df = pd.read_csv(path)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["timestamp"] = pd.to_datetime(
        df["order_date"].astype(str) + " " + df["order_time"].astype(str),
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )
    return df


def reload_brigade_data() -> None:
    """Clear cached CSV after file changes."""
    _load_dataframe.cache_clear()


def get_dashboard() -> dict[str, Any]:
    """Full dashboard payload from Brigade POS CSV."""
    df = _load_dataframe()
    order_revenue = df.groupby("order_id")["total_amount"].sum()

    store_name = str(df["store_name"].iloc[0]) if len(df) else "Brigade Bangalore"
    store_id = str(df["store_id"].iloc[0]) if len(df) else "ST1008"
    trade_date = (
        df["timestamp"].min().strftime("%d %B %Y")
        if df["timestamp"].notna().any()
        else "10 April 2026"
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
        df.groupby("product_name")["total_amount"]
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
    top_categories = (
        df.groupby("dep_name")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(6)
    )

    top_staff = (
        df[df["salesperson_name"].notna() & (df["salesperson_name"] != "")]
        .groupby("salesperson_name")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    return {
        "source": "Brigade_Bangalore_10_April_26 (1)bc6219c.csv",
        "store_name": store_name.replace("_", " "),
        "store_id": store_id,
        "date": trade_date,
        "summary": {
            "total_revenue": float(df["total_amount"].sum()),
            "total_orders": int(df["order_id"].nunique()),
            "line_items": int(len(df)),
            "unique_customers": int(df["customer_number"].nunique()),
            "average_order_value": float(order_revenue.mean()) if len(order_revenue) else 0.0,
            "average_items_per_order": float(len(df) / max(df["order_id"].nunique(), 1)),
        },
        "hourly_revenue": hourly_revenue,
        "top_products": [
            {"name": name[:60], "revenue": float(rev), "count": int(
                df[df["product_name"] == name]["qty"].sum()
            )}
            for name, rev in top_products.items()
        ],
        "top_brands": [
            {"name": name, "revenue": float(rev), "count": int(
                df[df["brand_name"] == name]["qty"].sum()
            )}
            for name, rev in top_brands.items()
        ],
        "top_categories": [
            {"name": name, "revenue": float(rev)} for name, rev in top_categories.items()
        ],
        "top_staff": [
            {"name": name, "revenue": float(rev)} for name, rev in top_staff.items()
        ],
    }


def get_pos_analytics() -> dict[str, Any]:
    """POS-shaped response for the sales page."""
    dashboard = get_dashboard()
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


def get_metrics() -> dict[str, Any]:
    """Metrics-shaped response for overview cards."""
    dashboard = get_dashboard()
    s = dashboard["summary"]
    return {
        "unique_visitors": s["unique_customers"],
        "active_visitors": s["unique_customers"],
        "conversion_rate": min(1.0, s["total_orders"] / max(s["unique_customers"], 1)),
        "revenue": s["total_revenue"],
        "average_dwell_time": 0,
        "queue_depth": 0,
        "timestamp": dashboard["date"],
        "store_name": dashboard["store_name"],
        "total_orders": s["total_orders"],
    }


def _events_dir() -> Path:
    return PROJECT_ROOT / "output" / "events"


def _camera_event_stats(camera_label: str) -> tuple[int, str]:
    """Count events in matching JSONL (e.g. CAM_1_events.jsonl for CAM 1)."""
    events_dir = _events_dir()
    if not events_dir.is_dir():
        return 0, "pending_processing"

    slug = camera_label.replace(" ", "_")
    num = camera_label.split()[-1] if " " in camera_label else camera_label
    candidates = [
        events_dir / f"{slug}_events.jsonl",
        events_dir / f"{camera_label}_events.jsonl",
        events_dir / f"CAM_{num}_events.jsonl",
    ]
    previews_dir = PROJECT_ROOT / "output" / "previews"
    for path in candidates:
        if path.is_file() and path.stat().st_size > 2:
            count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            if count > 0:
                return count, "processed"
    return 0, "pending_processing"


def _tracks_url(camera_label: str) -> str | None:
    """Per-frame bbox JSON for canvas overlay synced to video playback."""
    tracks_dir = PROJECT_ROOT / "output" / "tracks"
    slug = camera_label.replace(" ", "_")
    num = camera_label.split()[-1] if " " in camera_label else camera_label
    for name in (f"{slug}_tracks.json", f"CAM_{num}_tracks.json"):
        path = tracks_dir / name
        if path.is_file() and path.stat().st_size > 50:
            return f"/cctv-tracks/{name}"
    return None


def _preview_url(camera_label: str) -> str | None:
    """URL for annotated preview image if generated."""
    previews = PROJECT_ROOT / "output" / "previews"
    slug = camera_label.replace(" ", "_")
    for name in (f"{slug}_preview.jpg", f"{camera_label}_preview.jpg"):
        if (previews / name).is_file():
            return f"/cctv-previews/{name}"
    return None


def list_cctv_footage() -> dict[str, Any]:
    """List Purple-provided CCTV files for Brigade store."""
    cctv_dir = _cctv_dir()
    cameras = []

    if cctv_dir.is_dir():
        for idx, video in enumerate(sorted(cctv_dir.glob("*.mp4")), start=1):
            size_mb = video.stat().st_size / (1024 * 1024)
            event_count, pipeline_status = _camera_event_stats(video.stem)
            preview = _preview_url(video.stem)
            tracks = _tracks_url(video.stem)
            cameras.append(
                {
                    "id": f"CAM-{idx}",
                    "name": video.stem,
                    "file_name": video.name,
                    "media_url": f"/cctv-media/{video.name}",
                    "tracks_url": tracks,
                    "preview_url": preview,
                    "annotated_video_url": (
                        f"/cctv-previews/{video.stem.replace(' ', '_')}_annotated.mp4"
                        if (PROJECT_ROOT / "output" / "previews" / f"{video.stem.replace(' ', '_')}_annotated.mp4").is_file()
                        else None
                    ),
                    "size_mb": round(size_mb, 1),
                    "status": "footage_available",
                    "pipeline_status": pipeline_status,
                    "event_count": event_count,
                    "visitor_count": event_count,
                    "active_tracks": 0,
                    "last_frame_timestamp": None,
                }
            )

    return {
        "store_name": "Brigade Bangalore",
        "footage_date": "10 April 2026",
        "cameras": cameras,
        "total": len(cameras),
        "note": (
            "Run: python scripts/process_brigade_cctv.py — events land in output/events/. "
            "API auto-loads JSONL on startup for /stores/ST1008/metrics."
        ),
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }
