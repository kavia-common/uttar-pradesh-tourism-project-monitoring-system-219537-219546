from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import FastAPI
from src.api.config import get_settings
import asyncio
from typing import Optional

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


# PUBLIC_INTERFACE
def get_db() -> AsyncIOMotorDatabase:
    """Get the Mongo database instance (initialized in app startup)."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    try:
        # Users
        await db.users.create_index("email", unique=True)
        await db.users.create_index("roles")
        # Roles
        await db.roles.create_index("name", unique=True)
        # Projects
        await db.projects.create_index("code", unique=True)
        await db.projects.create_index([("location", "2dsphere")])
        # Progress images metadata
        await db.progress_images.create_index([("location", "2dsphere")])
        await db.progress_images.create_index("project_id")
        # Generic created_at indexes
        for name in [
            "tenders", "contractors", "funds", "milestones",
            "progress", "inspections", "handover", "payments", "audit_logs"
        ]:
            await db[name].create_index("created_at")
    except Exception:
        # Index creation failures shouldn't block app startup in dev
        pass


# PUBLIC_INTERFACE
async def init_app_state(app: FastAPI) -> None:
    """Initialize global Mongo client on startup and attach to app state with timeout and retry safety."""
    global _client, _db
    settings = get_settings()
    try:
        # Set a short serverSelectionTimeoutMS to avoid long hangs at startup if DB is unreachable
        _client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        _db = _client[settings.MONGODB_DB]
        # Force a quick ping to validate connection but don't crash the app if it fails (log best-effort)
        try:
            await asyncio.wait_for(_db.command("ping"), timeout=3.5)
        except Exception:
            # If ping fails, keep client; routes that need DB will still raise via get_db
            pass
        # Best-effort index creation
        await _create_indexes(_db)
        app.state.mongo_client = _client
        app.state.mongo_db = _db
    except Exception:
        # Ensure app state is set even if connection failed to avoid attribute errors
        _client = None
        _db = None
        app.state.mongo_client = None
        app.state.mongo_db = None


# PUBLIC_INTERFACE
async def close_app_state(app: FastAPI) -> None:
    """Close Mongo client on shutdown."""
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None
    app.state.mongo_client = None
    app.state.mongo_db = None
