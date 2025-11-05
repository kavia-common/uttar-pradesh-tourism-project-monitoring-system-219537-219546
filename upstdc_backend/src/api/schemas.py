from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


# Auth / Users

class RoleModel(BaseModel):
    name: str = Field(..., description="Role name e.g. admin, manager, auditor")
    permissions: List[str] = Field(default_factory=list, description="Permission strings")


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    roles: List[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")


class UserPublic(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    full_name: str
    roles: List[str] = Field(default_factory=list)


# Common Entities

class Project(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    # GeoJSON Point or Polygon for project location/extent
    location: Optional[dict] = Field(default=None, description="GeoJSON geometry")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressImageMeta(BaseModel):
    project_id: str
    file_key: str
    url: Optional[str] = None
    exif: dict = Field(default_factory=dict)
    location: Optional[dict] = None
    captured_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeoBBoxQuery(BaseModel):
    bbox: List[float] = Field(..., description="minLon,minLat,maxLon,maxLat")


class GeoNearQuery(BaseModel):
    lon: float
    lat: float
    max_distance_m: int = 1000


class ReportResponse(BaseModel):
    filename: str
    content_type: str = "text/csv"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
