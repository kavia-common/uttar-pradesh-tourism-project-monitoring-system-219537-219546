from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from src.api.security import rbac_required
from src.api.db.mongo import get_db
from src.api.schemas import Project

router = APIRouter(prefix="/core", tags=["Core Entities"])


def _now():
    return datetime.utcnow()


async def _ensure_exists(col, _id: str, name: str):
    doc = await col.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return doc


# Users minimal admin listing for RBAC verification
@router.get("/users", dependencies=[Depends(rbac_required(required_roles=["admin"]))])
async def list_users(limit: int = 50, skip: int = 0):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    users = await db.users.find({}, {"password_hash": 0}).skip(skip).limit(limit).to_list(length=limit)
    for u in users:
        u["_id"] = str(u["_id"])
    return {"items": users, "count": len(users)}


# Projects CRUD
@router.post("/projects", dependencies=[Depends(rbac_required(required_roles=["admin", "manager"]))])
async def create_project(project: Project):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    data = project.model_dump()
    data["created_at"] = _now()
    data["updated_at"] = _now()
    await db.projects.insert_one(data)
    data["_id"] = data["code"]
    return data


@router.get("/projects")
async def list_projects(limit: int = 50, skip: int = 0):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    items = await db.projects.find({}).skip(skip).limit(limit).to_list(length=limit)
    for i in items:
        i["_id"] = i.get("code")
    return {"items": items, "count": len(items)}


@router.get("/projects/{code}")
async def get_project(code: str):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = await db.projects.find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    doc["_id"] = doc.get("code")
    return doc


@router.put("/projects/{code}", dependencies=[Depends(rbac_required(required_roles=["admin", "manager"]))])
async def update_project(code: str, payload: dict):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    payload["updated_at"] = _now()
    res = await db.projects.update_one({"code": code}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    doc = await db.projects.find_one({"code": code})
    doc["_id"] = doc.get("code")
    return doc


@router.delete("/projects/{code}", dependencies=[Depends(rbac_required(required_roles=["admin"]))])
async def delete_project(code: str):
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    res = await db.projects.delete_one({"code": code})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "code": code}


# Skeleton CRUD routes for domain entities to satisfy acceptance criteria
ENTITIES = ["tenders", "contractors", "funds", "milestones", "progress", "inspections", "handover", "payments"]


@router.post("/{entity}", dependencies=[Depends(rbac_required(required_roles=["admin", "manager"]))])
async def create_entity(entity: str, payload: dict):
    if entity not in ENTITIES:
        raise HTTPException(status_code=404, detail="Unknown entity")
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    payload["created_at"] = _now()
    result = await db[entity].insert_one(payload)
    payload["_id"] = str(result.inserted_id)
    return payload


@router.get("/{entity}")
async def list_entity(entity: str, limit: int = 50, skip: int = 0):
    if entity not in ENTITIES:
        raise HTTPException(status_code=404, detail="Unknown entity")
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    items = await db[entity].find({}).skip(skip).limit(limit).to_list(length=limit)
    for i in items:
        i["_id"] = str(i["_id"])
    return {"items": items, "count": len(items)}
