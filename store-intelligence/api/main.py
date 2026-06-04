"""
FastAPI Application Factory

Main entry point for the REST API.
Configures FastAPI application with all middleware, routes, and error handlers.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from configs import get_settings, setup_logging
from storage import init_db, close_db

logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Context Manager
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, logging
    - Shutdown: Close database connections
    """
    # ========================================================================
    # Startup
    # ========================================================================
    logger.info("Application starting up...")
    settings = get_settings()
    setup_logging(settings)
    
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(
            f"Database initialization warning: {e}. "
            "Application will start but database-dependent features may not work."
        )

    try:
        from api.bootstrap_data import bootstrap_all_stores
        from storage.jsonl_event_store import get_jsonl_event_store

        get_jsonl_event_store().load_from_disk()
        bootstrap_all_stores()
    except Exception as e:
        logger.warning("Store bootstrap skipped: %s", e)

    yield  # Application runs here

    # ========================================================================
    # Shutdown
    # ========================================================================
    logger.info("Application shutting down...")
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Database shutdown error: {e}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # ========================================================================
    # Create FastAPI Application
    # ========================================================================
    app = FastAPI(
        title=settings.app_name,
        description="Production-grade Store Intelligence Analytics Platform",
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ========================================================================
    # CORS Middleware
    # ========================================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # ========================================================================
    # Health Check Endpoint
    # ========================================================================
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }

    @app.get("/ready")
    async def readiness_check():
        """Readiness check endpoint for Kubernetes."""
        return {
            "ready": True,
            "app": settings.app_name,
        }

    # ========================================================================
    # Exception Handlers
    # ========================================================================
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with structured response."""
        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors with structured response."""
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
        )

    # ========================================================================
    # Include Routers
    # ========================================================================
    from api.routes.analytics import create_analytics_router, register_spec_routes
    from api.routes.brigade import router as brigade_router
    from api.routes.stores import router as stores_router
    from api.services.store_catalog import list_stores

    app.include_router(create_analytics_router())
    register_spec_routes(app)
    app.include_router(stores_router)
    app.include_router(brigade_router)
    logger.info("Analytics routes registered")
    logger.info("Store routes registered")

    project_root = Path(__file__).resolve().parents[1]
    for store in list_stores():
        media_dir = store.root
        if media_dir.is_dir():
            mount_path = f"/store-media/{store.slug}"
            app.mount(
                mount_path,
                StaticFiles(directory=str(media_dir)),
                name=f"store-media-{store.slug}",
            )
            logger.info("Store media mounted at %s from %s", mount_path, media_dir)

    tracks_root = project_root / "output"
    tracks_root.mkdir(parents=True, exist_ok=True)
    app.mount("/cctv-tracks", StaticFiles(directory=str(tracks_root)), name="cctv-tracks")
    logger.info("Track JSON mounted at /cctv-tracks from %s", tracks_root)

    logger.info(f"FastAPI application created: {settings.app_name} v{settings.app_version}")

    return app


# ============================================================================
# Application Instance
# ============================================================================
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from configs import get_settings

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
