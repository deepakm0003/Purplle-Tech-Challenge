"""
Store 1 / Store 2 API routes.
"""

from fastapi import APIRouter, HTTPException, Query

from api.services.store_service import (
    get_dashboard,
    get_pos_analytics,
    list_cameras,
    list_stores_summary,
    reload_pos_cache,
)

router = APIRouter(prefix="/api/stores", tags=["stores"])


@router.get("")
async def stores_list():
    return list_stores_summary()


@router.get("/{store_id}/dashboard")
async def store_dashboard(store_id: str):
    try:
        return get_dashboard(store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{store_id}/pos")
async def store_pos(store_id: str):
    try:
        return get_pos_analytics(store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{store_id}/cameras")
async def store_cameras(store_id: str):
    try:
        return list_cameras(store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reload")
async def stores_reload():
    reload_pos_cache()
    return {"success": True, "message": "Store data cache cleared"}
