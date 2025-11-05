from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from src.api.security import rbac_required
from src.api.db.mongo import get_db
from src.api.storage import upload_bytes
from src.api.config import get_settings
from src.api.utils.exif import extract_gps_from_bytes, make_geojson_point

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/progress-image", dependencies=[Depends(rbac_required(required_roles=["admin", "manager", "engineer"]))])
async def upload_progress_image(
    project_id: str = Form(...),
    image: UploadFile = File(...),
):
    settings = get_settings()
    if not settings.S3_BUCKET:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    data = await image.read()
    lat, lon, exif = extract_gps_from_bytes(data)
    location = None
    if lat is not None and lon is not None:
        location = make_geojson_point(lat, lon)

    key = f"progress/{project_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}"
    public_url = upload_bytes(settings.S3_BUCKET, key, data, image.content_type or "application/octet-stream")

    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = {
        "project_id": project_id,
        "file_key": key,
        "url": public_url,
        "exif": exif,
        "location": location,
        "captured_at": None,
        "created_at": datetime.utcnow(),
    }
    await db.progress_images.insert_one(doc)
    doc["_id"] = key
    return doc
