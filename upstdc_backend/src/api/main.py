from fastapi import FastAPI, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.config import get_settings, get_cors_origins
from src.api.db.mongo import init_app_state, close_app_state
from src.api.middleware import AuditMiddleware

from src.api.routes.auth import router as auth_router
from src.api.routes.core import router as core_router
from src.api.routes.uploads import router as uploads_router
from src.api.routes.geo import router as geo_router
from src.api.routes.reports import router as reports_router
from src.api.schemas import Project


# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """Create and configure FastAPI app with middleware, routers, and lifecycle events.

    This function loads Settings inside the factory to avoid import-time evaluation,
    ensuring environment variables and .env are parsed at runtime.
    """
    settings = get_settings()

    openapi_tags = [
        {"name": "Auth", "description": "Authentication and user session"},
        {"name": "Core Entities", "description": "Users, projects, and domain data"},
        {"name": "Uploads", "description": "File uploads and metadata"},
        {"name": "Geo", "description": "Geospatial queries and data"},
        {"name": "Reports", "description": "CSV reporting endpoints"},
    ]

    app = FastAPI(
        title=settings.APP_NAME,
        description="UPSTDC Project Monitoring System API",
        version=settings.APP_VERSION,
        openapi_tags=openapi_tags,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(settings),
        allow_credentials=True,
        allow_methods=settings.cors_methods_list() or ["*"],
        allow_headers=settings.cors_headers_list() or ["*"],
    )

    # Rate limiter
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Audit middleware
    app.add_middleware(AuditMiddleware)

    # Mount routers under /api/v1
    api = APIRouter(prefix="/api/v1")
    api.include_router(auth_router)
    api.include_router(core_router)
    api.include_router(uploads_router)
    api.include_router(geo_router)
    api.include_router(reports_router)
    app.include_router(api)

    # Backward-compatibility shims for older frontend paths without version/core prefixes.
    # These forward to the same logic as core routes to prevent 404s when frontend calls /api/projects.
    legacy_api = APIRouter(prefix="/api", tags=["Core Entities"])

    # Reuse handler functions by importing from core router module
    from src.api.routes.core import (
        create_project as _create_project,
        list_projects as _list_projects,
        get_project as _get_project,
        update_project as _update_project,
        delete_project as _delete_project,
    )

    # PUBLIC_INTERFACE
    @legacy_api.post(
        "/projects",
        summary="Create Project (legacy path)",
        responses={200: {"description": "Successful Response"}},
    )
    async def legacy_create_project(project: Project):
        """Compatibility endpoint mapping to /api/v1/core/projects (POST)."""
        return await _create_project(project)

    # PUBLIC_INTERFACE
    @legacy_api.get(
        "/projects",
        summary="List Projects (legacy path)",
        responses={200: {"description": "Successful Response"}},
    )
    async def legacy_list_projects(limit: int = 50, skip: int = 0):
        """Compatibility endpoint mapping to /api/v1/core/projects (GET)."""
        return await _list_projects(limit=limit, skip=skip)

    # PUBLIC_INTERFACE
    @legacy_api.get(
        "/projects/{code}",
        summary="Get Project (legacy path)",
        responses={200: {"description": "Successful Response"}},
    )
    async def legacy_get_project(code: str):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (GET)."""
        return await _get_project(code)

    # PUBLIC_INTERFACE
    @legacy_api.put(
        "/projects/{code}",
        summary="Update Project (legacy path)",
        responses={200: {"description": "Successful Response"}},
    )
    async def legacy_update_project(code: str, payload: dict = Body(...)):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (PUT)."""
        return await _update_project(code, payload)

    # PUBLIC_INTERFACE
    @legacy_api.delete(
        "/projects/{code}",
        summary="Delete Project (legacy path)",
        responses={200: {"description": "Successful Response"}},
    )
    async def legacy_delete_project(code: str):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (DELETE)."""
        return await _delete_project(code)

    # Also accept completely unversioned legacy path '/projects' if some frontends bypass '/api' prefix.
    # This router is intentionally minimal and forwards to same handlers.
    bare_legacy_api = APIRouter(prefix="", tags=["Core Entities"])

    # PUBLIC_INTERFACE
    @bare_legacy_api.post("/projects", summary="Create Project (bare legacy path)")
    async def bare_legacy_create_project(project: Project):
        """Compatibility endpoint mapping to /api/v1/core/projects (POST) for bare path."""
        return await _create_project(project)

    # PUBLIC_INTERFACE
    @bare_legacy_api.get("/projects", summary="List Projects (bare legacy path)")
    async def bare_legacy_list_projects(limit: int = 50, skip: int = 0):
        """Compatibility endpoint mapping to /api/v1/core/projects (GET) for bare path."""
        return await _list_projects(limit=limit, skip=skip)

    # PUBLIC_INTERFACE
    @bare_legacy_api.get("/projects/{code}", summary="Get Project (bare legacy path)")
    async def bare_legacy_get_project(code: str):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (GET) for bare path."""
        return await _get_project(code)

    # PUBLIC_INTERFACE
    @bare_legacy_api.put("/projects/{code}", summary="Update Project (bare legacy path)")
    async def bare_legacy_update_project(code: str, payload: dict = Body(...)):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (PUT) for bare path."""
        return await _update_project(code, payload)

    # PUBLIC_INTERFACE
    @bare_legacy_api.delete("/projects/{code}", summary="Delete Project (bare legacy path)")
    async def bare_legacy_delete_project(code: str):
        """Compatibility endpoint mapping to /api/v1/core/projects/{code} (DELETE) for bare path."""
        return await _delete_project(code)

    # Include legacy routers
    app.include_router(legacy_api)
    app.include_router(bare_legacy_api)

    @app.on_event("startup")
    async def on_startup():
        await init_app_state(app)

    @app.on_event("shutdown")
    async def on_shutdown():
        await close_app_state(app)

    @app.get("/", tags=["Misc"], summary="Health Check")
    def health_check():
        """Health check endpoint."""
        settings_inner = get_settings()
        return {"message": "Healthy", "version": settings_inner.APP_VERSION}

    @app.get("/healthz", tags=["Misc"], summary="Health Check (Probes)")
    async def healthz():
        """Lightweight health probe endpoint for load balancers and Nginx."""
        settings_inner = get_settings()
        # Do not await DB here; only report version. Always return 200 quickly.
        return {"status": "ok", "version": settings_inner.APP_VERSION}

    @app.get("/api/v1/db/status", tags=["Misc"], summary="DB status (non-blocking)")
    async def db_status():
        """Return MongoDB reachability with small timeout; does not block app startup."""
        from src.api.db.mongo import mongo_reachability
        status = await mongo_reachability()
        code = 200 if status.get("ok") else 503
        return JSONResponse(status_code=code, content=status)

    @app.get("/api/v1/docs/websocket-usage", tags=["Misc"], summary="WebSocket Usage")
    def websocket_usage():
        """WebSocket usage note placeholder for real-time endpoints (if added in future).

        Also note: REST base path for project APIs is /api/v1/core/projects.
        Legacy shims are temporarily available at /api/projects to ease migration, but
        new frontend code should prefer the versioned path.
        """
        return {
            "note": "No active WebSocket endpoints. Future real-time updates will be documented here.",
            "rest_project_base": "/api/v1/core/projects",
            "legacy_project_base": "/api/projects",
        }

    return app


# PUBLIC_INTERFACE
def get_app() -> FastAPI:
    """ASGI application factory accessor; prevents import-time side effects by creating the app on demand."""
    return create_app()


# IMPORTANT: Expose a module-level ASGI app for uvicorn 'src.api.main:app'
# Recommended run command:
#   uvicorn src.api.main:app --host 0.0.0.0 --port 3001
# Alternatively, factory mode:
#   uvicorn src.api.main:get_app --factory --host 0.0.0.0 --port 3001
# Keep creation lightweight; heavy work executes in startup events.
app: FastAPI = create_app()
