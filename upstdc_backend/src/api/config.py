from functools import lru_cache
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables via pydantic-settings."""

    # App
    APP_NAME: str = "UPSTDC Project Monitoring API"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    SITE_URL: AnyUrl | None = None
    CORS_ORIGINS: str = "*"  # comma-separated

    # Mongo
    MONGODB_URL: str = Field(..., description="MongoDB connection string")
    MONGODB_DB: str = Field(..., description="MongoDB database name")

    # JWT
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # S3
    S3_ENDPOINT_URL: str | None = None  # For S3-compatible storage (e.g., MinIO)
    S3_REGION: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET: str | None = None
    S3_PUBLIC_BASE_URL: str | None = None  # Optional CDN/public URL prefix

    # Rate limit
    RATE_LIMIT: str = "100/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


# PUBLIC_INTERFACE
def get_cors_origins(settings: "Settings") -> list[str]:
    """Parse comma-separated CORS origins into list."""
    if not settings.CORS_ORIGINS:
        return []
    if settings.CORS_ORIGINS.strip() == "*":
        return ["*"]
    return [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
