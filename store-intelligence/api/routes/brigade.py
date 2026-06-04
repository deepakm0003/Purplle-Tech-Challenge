"""
Legacy /api/brigade routes — alias to Store 1 (ST1008) for older dashboard builds.
"""

from fastapi import APIRouter, HTTPException

from api.routes.analytics import get_analytics_service
from api.services.store_service import (
    get_dashboard,
    get_pos_analytics,
    list_cameras,
    reload_pos_cache,
)

router = APIRouter(prefix="/api/brigade", tags=["brigade"])
DEFAULT_STORE = "ST1008"


@router.get("/dashboard")
async def brigade_dashboard():
    try:
        return get_dashboard(DEFAULT_STORE)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/metrics")
async def brigade_metrics():
    try:
        svc = get_analytics_service(DEFAULT_STORE)
        if svc.events:
            m = svc.compute_all_analytics()["metrics"]
            dash = get_dashboard(DEFAULT_STORE)
            return {
                "unique_visitors": m.get("unique_visitors", 0),
                "active_visitors": m.get("store_footfall", m.get("unique_visitors", 0)),
                "conversion_rate": m.get("conversion_rate", 0),
                "revenue": m.get("revenue", 0),
                "average_dwell_time": m.get("average_dwell_time", 0),
                "queue_depth": m.get("queue_depth", 0),
                "timestamp": dash["date"],
                "store_name": dash["store_name"],
                "total_orders": dash["summary"]["total_orders"],
            }
        dash = get_dashboard(DEFAULT_STORE)
        s = dash["summary"]
        return {
            "unique_visitors": s["unique_customers"],
            "active_visitors": s["unique_customers"],
            "conversion_rate": min(1.0, s["total_orders"] / max(s["unique_customers"], 1)),
            "revenue": s["total_revenue"],
            "average_dwell_time": 0,
            "queue_depth": 0,
            "timestamp": dash["date"],
            "store_name": dash["store_name"],
            "total_orders": s["total_orders"],
        }
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/pos")
async def brigade_pos():
    try:
        return get_pos_analytics(DEFAULT_STORE)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cameras")
async def brigade_cameras():
    return list_cameras(DEFAULT_STORE)


@router.post("/reload")
async def brigade_reload():
    reload_pos_cache()
    return {"success": True, "message": "Store data cache cleared"}