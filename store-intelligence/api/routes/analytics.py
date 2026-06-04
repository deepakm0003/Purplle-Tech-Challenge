"""
Analytics Routes.

Analytics API endpoints for store intelligence.

Endpoints:
- POST /events/ingest - Ingest event batch
- GET /stores/{store_id}/metrics - Store metrics
- GET /stores/{store_id}/funnel - Conversion funnel
- GET /stores/{store_id}/heatmap - Zone heatmap
- GET /stores/{store_id}/anomalies - Detected anomalies
- GET /health - Health check
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DatabaseSession
from api.schemas import Event
from api.schemas.analytics import (
    AnomaliesResponse,
    EventIngestRequest,
    EventIngestResponse,
    FunnelResponse,
    HealthResponse,
    HealthStatus,
    HeatmapResponse,
    MetricsResponse,
)
from api.services.analytics_service import AnalyticsService
from storage.jsonl_event_store import get_jsonl_event_store
from storage.repositories.event_repository import EventRepository

logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

_analytics_services: dict[str, AnalyticsService] = {}


def get_analytics_service(store_id: str) -> AnalyticsService:
    """Get or create analytics service for a store."""
    if store_id not in _analytics_services:
        _analytics_services[store_id] = AnalyticsService(store_id)
    return _analytics_services[store_id]


async def _load_store_events(session: AsyncSession, store_id: str) -> list[Event]:
    """Load events from JSONL pipeline output + DB, refresh analytics service."""
    jsonl_store = get_jsonl_event_store()
    jsonl_store.load_from_disk()
    events = jsonl_store.load_events_for_store(store_id)

    repo = EventRepository(session)
    try:
        db_events = await repo.get_pydantic_events_for_store(store_id, limit=10000)
        seen = {e.event_id for e in events}
        for e in db_events:
            if e.event_id not in seen:
                events.append(e)
                seen.add(e.event_id)
    except Exception as exc:
        logger.warning(f"Could not load DB events for {store_id}: {exc}")

    svc = get_analytics_service(store_id)
    if events:
        svc.ingest_events(events, replace=True)

    from api.services.store_catalog import pos_csv_path

    pos_path = pos_csv_path()
    if pos_path.exists() and not getattr(svc, "_pos_loaded", False):
        svc.load_pos_data(str(pos_path))
        svc._pos_loaded = True

    return events


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/events/ingest", response_model=EventIngestResponse, status_code=202)
async def ingest_events(
    request: EventIngestRequest,
    session: DatabaseSession,
) -> EventIngestResponse:
    """Ingest up to 500 events per batch with idempotent deduplication."""
    if len(request.events) > 500:
        raise HTTPException(status_code=400, detail="Batch exceeds 500 events")

    repo = EventRepository(session)
    total = len(request.events)
    ingested = 0
    failed = 0
    failed_ids: list[str] = []

    logger.info(f"Ingesting batch of {total} events")

    for idx, event_data in enumerate(request.events):
        try:
            event = Event(**event_data)

            if await repo.deduplicate_by_event_id(event.event_id):
                logger.debug(f"Event {event.event_id} already exists, skipping")
                continue

            jsonl_store = get_jsonl_event_store()
            if not jsonl_store.append(event):
                continue

            get_analytics_service(event.store_id).ingest_events([event])
            ingested += 1

        except ValidationError as exc:
            logger.warning(f"Validation error for event {idx}: {exc}")
            failed += 1
            if "event_id" in event_data:
                failed_ids.append(str(event_data["event_id"]))
        except Exception as exc:
            logger.error(f"Error ingesting event {idx}: {exc}")
            failed += 1
            if "event_id" in event_data:
                failed_ids.append(str(event_data["event_id"]))

    return EventIngestResponse(
        success=failed == 0,
        message=f"Ingested {ingested}/{total} events",
        total=total,
        ingested=ingested,
        failed=failed,
        failed_ids=failed_ids,
        timestamp=datetime.utcnow(),
    )


@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
async def get_store_metrics(
    store_id: str,
    session: DatabaseSession,
) -> MetricsResponse:
    """Get store metrics computed from ingested events."""
    await _load_store_events(session, store_id)
    metrics = get_analytics_service(store_id).get_metrics()

    return MetricsResponse(
        success=True,
        message="Metrics computed",
        unique_visitors=metrics["unique_visitors"],
        conversion_rate=metrics["conversion_rate"],
        average_dwell_time=metrics["average_dwell_time"],
        average_dwell_by_zone=metrics["average_dwell_by_zone"],
        queue_depth=metrics["queue_depth"],
        abandonment_rate=metrics["abandonment_rate"],
        revenue=metrics["revenue"],
        average_basket_size=metrics["average_basket_size"],
        store_footfall=metrics["store_footfall"],
        zone_visit_frequency=metrics["zone_visit_frequency"],
        timestamp=datetime.utcnow(),
    )


@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def get_funnel(
    store_id: str,
    session: DatabaseSession,
) -> FunnelResponse:
    """Get conversion funnel for a store."""
    await _load_store_events(session, store_id)
    funnel = get_analytics_service(store_id).get_funnel()

    return FunnelResponse(
        success=True,
        message="Funnel computed",
        entry_count=funnel["entry_count"],
        zone_count=funnel["zone_count"],
        billing_count=funnel["billing_count"],
        purchase_count=funnel["purchase_count"],
        dropoff_percentages=funnel["dropoff_percentages"],
        efficiency_percentage=funnel.get("efficiency_percentage", 0.0),
        timestamp=datetime.utcnow(),
    )


@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    store_id: str,
    session: DatabaseSession,
) -> HeatmapResponse:
    """Get zone heatmap for a store."""
    await _load_store_events(session, store_id)
    heatmap = get_analytics_service(store_id).get_heatmap()

    return HeatmapResponse(
        success=True,
        message="Heatmap computed",
        zones=heatmap["zones"],
        data_confidence=heatmap["data_confidence"],
        total_sessions=heatmap.get("total_sessions", 0),
        zone_count=heatmap.get("zone_count", len(heatmap.get("zones", []))),
        timestamp=datetime.utcnow(),
    )


@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(
    store_id: str,
    session: DatabaseSession,
) -> AnomaliesResponse:
    """Get detected anomalies for a store."""
    await _load_store_events(session, store_id)
    anomalies_data = get_analytics_service(store_id).get_anomalies()

    return AnomaliesResponse(
        success=True,
        message="Anomalies detected",
        total_anomalies=anomalies_data["total_anomalies"],
        critical=anomalies_data["critical"],
        warning=anomalies_data["warning"],
        info=anomalies_data["info"],
        anomalies=anomalies_data["anomalies"],
        timestamp=datetime.utcnow(),
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(session: DatabaseSession) -> HealthResponse:
    """Health check for database connectivity and feed staleness."""
    repo = EventRepository(session)
    overall_status = "UP"
    stale_warning = False
    last_event_timestamp = None

    try:
        await session.execute(text("SELECT 1"))
        db_status = HealthStatus(service="database", status="UP")
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        db_status = HealthStatus(service="database", status="DOWN", details=str(exc))
        overall_status = "DEGRADED"

    redis_status = HealthStatus(service="redis", status="UP")

    try:
        last_event = await repo.get_latest_event()
        if last_event:
            last_event_timestamp = last_event.timestamp
            now = datetime.utcnow()
            if last_event_timestamp.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            time_diff = (now - last_event_timestamp).total_seconds()
            if time_diff > 300:
                stale_warning = True
    except Exception as exc:
        logger.warning(f"Could not retrieve last event: {exc}")

    return HealthResponse(
        success=overall_status == "UP",
        message="Health check complete",
        status=overall_status,
        database=db_status,
        redis=redis_status,
        last_event_timestamp=last_event_timestamp,
        stale_feed_warning=stale_warning,
        checks=[db_status, redis_status],
        timestamp=datetime.utcnow(),
    )


@router.get("/stores/{store_id}/layout")
async def get_store_layout(store_id: str) -> dict:
    """Store floor plan for heatmap / map page (layout image, optional zones)."""
    config_dir = Path(__file__).resolve().parents[2] / "config"
    slug_map = {"ST1008": "store-1-layout.json", "ST2002": "store-2-layout.json"}
    layout_name = slug_map.get(store_id)
    if layout_name:
        path = config_dir / layout_name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))

    from api.services.store_catalog import get_store

    store = get_store(store_id)
    if store and store.layout_url():
        return {
            "store_id": store.id,
            "store_name": store.name,
            "layout_image_url": store.layout_url(),
            "zones": [],
        }

    fallback = config_dir / "store_layout.json"
    if fallback.is_file():
        return json.loads(fallback.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Store layout not found")


@router.get("/stores/{store_id}/events/summary")
async def get_events_summary(
    store_id: str,
    session: DatabaseSession,
) -> dict:
    """CCTV pipeline event counts for dashboard."""
    await _load_store_events(session, store_id)
    svc = get_analytics_service(store_id)
    entries = [e for e in svc.events if e.event_type.value == "ENTRY" and not e.is_staff]
    exits = sum(1 for e in svc.events if e.event_type.value == "EXIT")
    return {
        "store_id": store_id,
        "total_events": len(svc.events),
        "entry_events": len(entries),
        "exit_events": exits,
        "unique_visitors": len({e.visitor_id for e in entries}),
        "cameras": sorted({e.camera_id for e in svc.events}),
        "timestamp": datetime.utcnow().isoformat(),
    }


def create_analytics_router() -> APIRouter:
    """Factory to create analytics router."""
    return router


def register_spec_routes(app) -> None:
    """Challenge spec paths (no /api/analytics prefix) for acceptance tests."""
    app.add_api_route(
        "/events/ingest",
        ingest_events,
        methods=["POST"],
        tags=["spec"],
        response_model=EventIngestResponse,
        status_code=202,
    )
    app.add_api_route(
        "/stores/{store_id}/metrics",
        get_store_metrics,
        methods=["GET"],
        tags=["spec"],
        response_model=MetricsResponse,
    )
    app.add_api_route(
        "/stores/{store_id}/funnel",
        get_funnel,
        methods=["GET"],
        tags=["spec"],
        response_model=FunnelResponse,
    )
    app.add_api_route(
        "/stores/{store_id}/heatmap",
        get_heatmap,
        methods=["GET"],
        tags=["spec"],
        response_model=HeatmapResponse,
    )
    app.add_api_route(
        "/stores/{store_id}/anomalies",
        get_anomalies,
        methods=["GET"],
        tags=["spec"],
        response_model=AnomaliesResponse,
    )
