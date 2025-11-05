from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
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


# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """Create and configure FastAPI app with middleware, routers, and lifecycle events."""
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

    @app.get("/api/v1/docs/websocket-usage", tags=["Misc"], summary="WebSocket Usage")
    def websocket_usage():
        """WebSocket usage note placeholder for real-time endpoints (if added in future)."""
        return {
            "note": "No active WebSocket endpoints. Future real-time updates will be documented here."
        }

    return app


# Create module-level app for ASGI servers, but settings are only loaded within factory
app = create_app()
