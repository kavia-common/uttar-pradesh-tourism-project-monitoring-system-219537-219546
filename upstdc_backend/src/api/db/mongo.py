from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import FastAPI
from src.api.config import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


# PUBLIC_INTERFACE
def get_db() -> AsyncIOMotorDatabase:
    """Get the Mongo database instance (initialized in app startup)."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
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


# PUBLIC_INTERFACE
async def init_app_state(app: FastAPI) -> None:
    """Initialize global Mongo client on startup and attach to app state."""
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    _db = _client[settings.MONGODB_DB]
    await _create_indexes(_db)
    app.state.mongo_client = _client
    app.state.mongo_db = _db


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
