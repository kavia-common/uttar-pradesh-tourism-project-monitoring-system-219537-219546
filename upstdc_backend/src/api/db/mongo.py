from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import FastAPI
from src.api.config import get_settings
import asyncio
from typing import Optional, Dict, Any
import urllib.parse

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _append_timeout_params(url: str) -> str:
    """
    Ensure short connect and serverSelection timeouts on the MongoDB URI.
    Adds/overrides connectTimeoutMS and serverSelectionTimeoutMS to 2000ms if not present.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        # Only set if not provided
        query.setdefault("connectTimeoutMS", "2000")
        query.setdefault("serverSelectionTimeoutMS", "2000")
        new_query = urllib.parse.urlencode(query)
        new_url = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )
        return new_url
    except Exception:
        # On any parsing issue, fall back to original URL
        return url


# PUBLIC_INTERFACE
def get_db() -> AsyncIOMotorDatabase:
    """Get the Mongo database instance. Lazily initializes client if necessary; raises if unavailable."""
    global _client, _db
    if _db is not None:
        return _db

    # Lazy init: create client quickly with short timeouts if not created yet
    settings = get_settings()
    try:
        mongo_url = _append_timeout_params(settings.MONGODB_URL)
        _client = AsyncIOMotorClient(mongo_url)
        _db_candidate = _client[settings.MONGODB_DB]
        # Do not block here; just set and let callers handle operational errors
        _db = _db_candidate
        return _db
    except Exception as e:
        # Keep None so callers can handle as service unavailable
        _client = None
        _db = None
        raise RuntimeError("Database not initialized") from e


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
    """Initialize global Mongo client on startup and attach to app state with timeout and retry safety.
    Does not block startup if DB is unreachable. Performs a best-effort ping with small timeout.
    """
    global _client, _db
    settings = get_settings()
    try:
        mongo_url = _append_timeout_params(settings.MONGODB_URL)
        _client = AsyncIOMotorClient(mongo_url)
        _db = _client[settings.MONGODB_DB]

        # Best-effort short ping; do not fail startup
        try:
            await asyncio.wait_for(_db.command("ping"), timeout=2.0)
            # Best-effort index creation but do not block if it takes too long
            try:
                await asyncio.wait_for(_create_indexes(_db), timeout=5.0)
            except Exception:
                pass
        except Exception:
            # keep client assigned; routes will handle failures
            pass

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


# PUBLIC_INTERFACE
async def mongo_reachability() -> Dict[str, Any]:
    """Return a lightweight status dict indicating if MongoDB is reachable within small timeout."""
    try:
        db = get_db()
        await asyncio.wait_for(db.command("ping"), timeout=2.0)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
