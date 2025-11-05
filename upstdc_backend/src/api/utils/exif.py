from typing import Optional, Dict, Any, Tuple
import exifread
from io import BytesIO


def _dms_to_decimal(dms, ref) -> Optional[float]:
    try:
        degrees = float(dms.values[0].num) / float(dms.values[0].den)
        minutes = float(dms.values[1].num) / float(dms.values[1].den)
        seconds = float(dms.values[2].num) / float(dms.values[2].den)
        sign = -1 if ref in ["S", "W"] else 1
        return sign * (degrees + minutes / 60 + seconds / 3600)
    except Exception:
        return None


# PUBLIC_INTERFACE
def extract_gps_from_bytes(data: bytes) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
    """Return (lat, lon, exif_dict) from image bytes using exifread."""
    tags = exifread.process_file(BytesIO(data), details=False)
    lat = lon = None
    if "GPS GPSLatitude" in tags and "GPS GPSLatitudeRef" in tags:
        lat = _dms_to_decimal(tags["GPS GPSLatitude"], str(tags["GPS GPSLatitudeRef"]))
    if "GPS GPSLongitude" in tags and "GPS GPSLongitudeRef" in tags:
        lon = _dms_to_decimal(tags["GPS GPSLongitude"], str(tags["GPS GPSLongitudeRef"]))
    # Convert tags to basic dict of str
    exif_basic = {k: str(v) for k, v in tags.items()}
    return lat, lon, exif_basic


# PUBLIC_INTERFACE
def make_geojson_point(lat: float, lon: float) -> dict:
    """Create a GeoJSON Point."""
    return {"type": "Point", "coordinates": [lon, lat]}
