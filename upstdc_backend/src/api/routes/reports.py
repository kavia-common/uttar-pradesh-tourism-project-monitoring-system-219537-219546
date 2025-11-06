import csv
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Response, Query, HTTPException
from src.api.db.mongo import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


def _csv_response(name: str, rows: List[List[str]]) -> Response:
    """Return a CSV streaming-like response for export endpoints."""
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


async def _safe_db() -> Any:
    """Get DB or raise HTTP 503 if unavailable."""
    try:
        return get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


def _now_utc() -> datetime:
    return datetime.utcnow()


# PUBLIC_INTERFACE
@router.get(
    "/projects-summary",
    summary="Project summary report (counts and aggregates)",
)
async def api_projects_summary():
    """Return a JSON summary with:
    - total_projects
    - counts_by_status (from 'status' field if present)
    - total_budget_inr (sum of budget_inr if present)
    - created_recent_30d (projects created in last 30 days)
    This endpoint is read-only and requires no authentication (guest mode).
    """
    db = await _safe_db()

    # Basic totals
    total_projects = await db.projects.count_documents({})

    # Counts by status (fallback to 'Unknown' if missing)
    pipeline_status = [
        {
            "$group": {
                "_id": {"$ifNull": ["$status", "Unknown"]},
                "count": {"$sum": 1},
            }
        }
    ]
    status_rows = await db.projects.aggregate(pipeline_status).to_list(length=100)
    counts_by_status: Dict[str, int] = {row["_id"]: int(row["count"]) for row in status_rows}

    # Budget aggregate if field exists
    pipeline_budget = [
        {"$match": {"budget_inr": {"$type": "number"}}},
        {"$group": {"_id": None, "total_budget_inr": {"$sum": "$budget_inr"}}},
    ]
    budget_rows = await db.projects.aggregate(pipeline_budget).to_list(length=1)
    total_budget_inr = int(budget_rows[0]["total_budget_inr"]) if budget_rows else 0

    # Recent creations - last 30 days
    since = _now_utc() - timedelta(days=30)
    created_recent_30d = await db.projects.count_documents({"created_at": {"$gte": since}})

    return {
        "generated_at": _now_utc().isoformat(),
        "totals": {
            "projects": total_projects,
            "budget_inr": total_budget_inr,
            "created_recent_30d": created_recent_30d,
        },
        "counts_by_status": counts_by_status,
    }


# PUBLIC_INTERFACE
@router.get(
    "/utilization-trend",
    summary="Monthly utilization trend (last 12 months)",
)
async def api_utilization_trend():
    """Return a monthly utilization trend for the last 12 months.
    If a 'utilization_monthly' collection or raw transactions are absent,
    compute a demo/fallback trend from project fields (budget_inr presence)
    to keep the UI functional in guest/demo mode.
    """
    db = await _safe_db()

    # Try to compute from a hypothetical collection 'utilization' if available
    since = _now_utc().replace(day=1) - timedelta(days=365)
    try:
        pipeline_util = [
            {"$match": {"month": {"$gte": since}}},
            {
                "$group": {
                    "_id": {
                        "y": {"$year": "$month"},
                        "m": {"$month": "$month"},
                    },
                    "utilization": {"$sum": "$amount_inr"},
                }
            },
            {"$sort": {"_id.y": 1, "_id.m": 1}},
        ]
        util_rows = await db.utilization.aggregate(pipeline_util).to_list(length=200)
    except Exception:
        util_rows = []

    series: List[Dict[str, Any]] = []
    if util_rows:
        for r in util_rows:
            y = r["_id"]["y"]
            m = r["_id"]["m"]
            series.append(
                {
                    "year": y,
                    "month": m,
                    "label": f"{y}-{m:02d}",
                    "value": int(r.get("utilization", 0)),
                }
            )
    else:
        # Fallback/demo computation:
        # Use total projects and budget presence to create a plausible trend.
        # Distribute total_budget_inr evenly, modulated with a simple curve.
        total_budget = 0
        try:
            b = await db.projects.aggregate(
                [
                    {"$match": {"budget_inr": {"$type": "number"}}},
                    {"$group": {"_id": None, "sum": {"$sum": "$budget_inr"}}},
                ]
            ).to_list(length=1)
            total_budget = int(b[0]["sum"]) if b else 0
        except Exception:
            total_budget = 0

        # Generate last 12 months
        today = _now_utc().replace(day=1)
        months: List[datetime] = []
        for i in range(12, 0, -1):
            # Walk back i months
            dt = (today - timedelta(days=30 * i))
            months.append(dt)

        base = max(total_budget // 120, 100000)  # base per month fallback
        for idx, dt in enumerate(months, start=1):
            # simple curve to add variation
            factor = 0.7 + (0.6 * ((idx % 6) / 6))
            val = int(base * factor)
            series.append(
                {
                    "year": dt.year,
                    "month": dt.month,
                    "label": f"{dt.year}-{dt.month:02d}",
                    "value": val,
                    "fallback": True,
                }
            )

    return {
        "generated_at": _now_utc().isoformat(),
        "series": series[-12:],  # ensure last 12 entries
        "unit": "INR",
    }


# PUBLIC_INTERFACE
@router.get(
    "/projects-list",
    summary="Project list report for export (CSV/JSON)",
)
async def api_projects_list(
    format: str = Query("json", pattern="^(json|csv)$"),
    limit: int = Query(1000, ge=1, le=5000),
    skip: int = Query(0, ge=0),
):
    """Return a list of projects with key fields for export.
    - Default JSON: compact list with key fields.
    - If format=csv: returns a CSV attachment.
    Fields: code, name, status, district, budget_inr, created_at, updated_at
    """
    db = await _safe_db()
    cursor = (
        db.projects.find(
            {},
            {
                "code": 1,
                "name": 1,
                "status": 1,
                "district": 1,
                "budget_inr": 1,
                "created_at": 1,
                "updated_at": 1,
            },
        )
        .skip(skip)
        .limit(limit)
        .sort("code", 1)
    )
    items = await cursor.to_list(length=limit or 1000)

    # Prepare consistent records
    def _rowify(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "code": doc.get("code"),
            "name": doc.get("name"),
            "status": doc.get("status", "Unknown"),
            "district": doc.get("district", ""),
            "budget_inr": int(doc.get("budget_inr", 0) or 0),
            "created_at": (doc.get("created_at") or "").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
            "updated_at": (doc.get("updated_at") or "").isoformat() if isinstance(doc.get("updated_at"), datetime) else str(doc.get("updated_at", "")),
        }

    rows = [_rowify(d) for d in items]

    if format == "csv":
        # header + rows
        header = ["code", "name", "status", "district", "budget_inr", "created_at", "updated_at"]
        csv_rows: List[List[str]] = [header]
        for r in rows:
            csv_rows.append(
                [
                    r["code"] or "",
                    r["name"] or "",
                    r["status"] or "",
                    r["district"] or "",
                    str(r["budget_inr"]),
                    r["created_at"] or "",
                    r["updated_at"] or "",
                ]
            )
        return _csv_response("projects_list.csv", csv_rows)

    return {
        "generated_at": _now_utc().isoformat(),
        "count": len(rows),
        "items": rows,
    }


# PUBLIC_INTERFACE
@router.get(
    "/legacy/projects-list",
    summary="Legacy shim for projects list report (CSV/JSON)",
)
async def legacy_projects_list(
    format: str = Query("json", pattern="^(json|csv)$"),
    limit: int = Query(1000, ge=1, le=5000),
    skip: int = Query(0, ge=0),
):
    """Legacy shim kept under /api/reports via router inclusion in main to ease migration.
    Mirrors /api/v1/reports/projects-list.
    """
    return await api_projects_list(format=format, limit=limit, skip=skip)
