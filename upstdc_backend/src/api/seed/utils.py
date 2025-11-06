import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from fastapi import APIRouter, HTTPException
from src.api.db.mongo import get_db

SEED_DIR = Path(__file__).parent
SEED_FILE = SEED_DIR / "projects_seed.json"

router = APIRouter(prefix="/seed", tags=["Core Entities"])


def _now():
    return datetime.utcnow()


async def _ensure_indexes():
    """Best-effort ensure indexes relevant to projects seeding."""
    try:
        db = get_db()
        await db.projects.create_index("code", unique=True)
        await db.projects.create_index([("location", "2dsphere")])
    except Exception:
        # do not block seeding if indexing fails in dev
        pass


def _read_seed_file() -> List[Dict[str, Any]]:
    if not SEED_FILE.exists():
        return []
    try:
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


async def _upsert_project(p: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Insert project if not exists by code. Returns (inserted, error)."""
    try:
        db = get_db()
    except Exception:
        return False, "Database unavailable"

    code = p.get("code")
    if not code:
        return False, "Missing code"

    # Ensure timestamps
    p.setdefault("created_at", _now())
    p["updated_at"] = _now()

    # Upsert by code but only insert if not existing
    try:
        existing = await db.projects.find_one({"code": code})
        if existing:
            return False, None
        await db.projects.insert_one(p)
        return True, None
    except Exception as e:
        return False, str(e)


# PUBLIC_INTERFACE
@router.post("/projects", summary="Seed demo projects (idempotent)")
async def seed_projects():
    """Seed a small set of demo projects for development and demos.
    Idempotent: existing codes are skipped. Returns counts and any errors.
    """
    await _ensure_indexes()
    seed = _read_seed_file()
    if not seed:
        raise HTTPException(status_code=500, detail="Seed file missing or invalid")

    inserted = 0
    errors: List[Dict[str, str]] = []
    for p in seed:
        ok, err = await _upsert_project(p)
        if ok:
            inserted += 1
        elif err:
            errors.append({"code": p.get("code", "?"), "error": err})

    return {"inserted": inserted, "skipped": len(seed) - inserted - len(errors), "errors": errors}


# PUBLIC_INTERFACE
async def seed_projects_on_startup() -> Dict[str, Any]:
    """Best-effort seeding during app startup. Non-fatal."""
    try:
        await _ensure_indexes()
        seed = _read_seed_file()
        if not seed:
            return {"inserted": 0, "skipped": 0, "errors": ["seed file missing"]}
        inserted = 0
        skipped = 0
        for p in seed:
            ok, err = await _upsert_project(p)
            if ok:
                inserted += 1
            else:
                if err is None:
                    skipped += 1
        return {"inserted": inserted, "skipped": skipped}
    except Exception:
        # Never fail startup
        return {"inserted": 0, "skipped": 0}
