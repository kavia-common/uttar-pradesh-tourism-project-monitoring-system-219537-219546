import csv
import io
from fastapi import APIRouter, Response, Depends
from src.api.security import rbac_required
from src.api.db.mongo import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


def _csv_response(name: str, rows: list[list[str]]):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for r in rows:
        writer.writerow(r)
    data = buffer.getvalue().encode("utf-8")
    headers = {
        "Content-Disposition": f'attachment; filename="{name}"',
        "Content-Type": "text/csv",
    }
    return Response(content=data, headers=headers, media_type="text/csv")


@router.get("/projects-summary", dependencies=[Depends(rbac_required(required_roles=["admin", "manager"]))])
async def projects_summary():
    try:
        db = get_db()
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")
    count = await db.projects.count_documents({})
    rows = [["metric", "value"], ["projects_total", str(count)]]
    return _csv_response("projects_summary.csv", rows)


@router.get("/funds-summary", dependencies=[Depends(rbac_required(required_roles=["admin", "finance"]))])
async def funds_summary():
    db = get_db()
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    agg = await db.funds.aggregate(pipeline).to_list(length=1)
    total = agg[0]["total"] if agg else 0
    rows = [["metric", "value"], ["funds_total", str(total)]]
    return _csv_response("funds_summary.csv", rows)


@router.get("/payments-summary", dependencies=[Depends(rbac_required(required_roles=["admin", "finance"]))])
async def payments_summary():
    db = get_db()
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    agg = await db.payments.aggregate(pipeline).to_list(length=1)
    total = agg[0]["total"] if agg else 0
    rows = [["metric", "value"], ["payments_total", str(total)]]
    return _csv_response("payments_summary.csv", rows)


@router.get("/milestones-progress", dependencies=[Depends(rbac_required(required_roles=["admin", "manager"]))])
async def milestones_progress():
    db = get_db()
    count = await db.milestones.count_documents({})
    rows = [["metric", "value"], ["milestones_count", str(count)]]
    return _csv_response("milestones_progress.csv", rows)


@router.get("/inspections-summary", dependencies=[Depends(rbac_required(required_roles=["admin", "auditor"]))])
async def inspections_summary():
    db = get_db()
    count = await db.inspections.count_documents({})
    rows = [["metric", "value"], ["inspections_count", str(count)]]
    return _csv_response("inspections_summary.csv", rows)
