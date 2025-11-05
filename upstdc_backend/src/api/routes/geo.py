from fastapi import APIRouter, Query
from src.api.db.mongo import get_db

router = APIRouter(prefix="/geo", tags=["Geo"])


@router.get("/progress/bbox")
async def progress_in_bbox(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
):
    db = get_db()
    query = {
        "location": {
            "$geoWithin": {
                "$geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [min_lon, min_lat],
                            [max_lon, min_lat],
                            [max_lon, max_lat],
                            [min_lon, max_lat],
                            [min_lon, min_lat],
                        ]
                    ],
                }
            }
        }
    }
    items = await db.progress_images.find(query).to_list(length=1000)
    features = []
    for doc in items:
        if not doc.get("location"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": doc["location"],
                "properties": {
                    "id": str(doc.get("_id", "")),
                    "project_id": doc.get("project_id"),
                    "url": doc.get("url"),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/progress/near")
async def progress_near(lon: float = Query(...), lat: float = Query(...), max_distance_m: int = Query(1000)):
    db = get_db()
    query = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": max_distance_m,
            }
        }
    }
    items = await db.progress_images.find(query).limit(200).to_list(length=200)
    features = []
    for doc in items:
        if not doc.get("location"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": doc["location"],
                "properties": {
                    "id": str(doc.get("_id", "")),
                    "project_id": doc.get("project_id"),
                    "url": doc.get("url"),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}
