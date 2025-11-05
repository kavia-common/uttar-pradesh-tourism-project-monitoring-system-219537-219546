from functools import lru_cache
from typing import List, Optional, Tuple
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

# Note: This module is fully Pydantic v2 compliant.
# Avoid any legacy 'class Config' or BaseSettings.Config usage.


class Settings(BaseSettings):
    """Application settings loaded from environment variables via pydantic-settings.

    All fields below are mapped from environment variables. Unknown variables are ignored.
    Comma-separated strings are supported for CORS lists. Env file is loaded from .env by default.
    """

    # App metadata
    APP_NAME: str = "UPSTDC Project Monitoring API"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    SITE_URL: AnyUrl | None = None

    # CORS (comma-separated strings accepted)
    CORS_ORIGINS: str = "*"  # e.g. "http://localhost:3000,https://example.com" or "*"
    CORS_METHODS: str = "*"  # e.g. "GET,POST,PUT,DELETE,OPTIONS" or "*"
    CORS_HEADERS: str = "*"  # e.g. "Authorization,Content-Type" or "*"
    CORS_CREDENTIALS: bool = True

    # Mongo
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection string")
    MONGODB_DB: str = Field(default="upstdc", description="MongoDB database name")

    # JWT (require presence via env, but fall back to dev-safe default to avoid crash in non-prod)
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-change-me",
        description="JWT secret key (set to a strong value in production via environment)",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Storage (defaults allow running without S3 in dev)
    USE_LOCAL_STORAGE: bool = Field(default=True, description="If true, store uploads on local filesystem")
    UPLOAD_DIR: str = Field(default="uploads", description="Local upload directory when USE_LOCAL_STORAGE=true")

    # URLs for frontend/backend
    BACKEND_URL: Optional[AnyUrl] = None
    FRONTEND_URL: Optional[AnyUrl] = None

    # S3
    S3_ENDPOINT_URL: str | None = None  # For S3-compatible storage (e.g., MinIO)
    S3_REGION: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET: str | None = None
    S3_PUBLIC_BASE_URL: str | None = None  # Optional CDN/public URL prefix

    # Rate limiting
    RATE_LIMIT: str = "100/minute"

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host binding")
    PORT: int = Field(default=3001, description="Server port")

    # Pydantic v2 Settings config only (no legacy Config). Adjust flags here if needed.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=True,
        # If equivalents were ever needed, set them here (examples):
        # validate_default=True,  # Pydantic v2 default behavior validates fields
        # arbitrary_types_allowed=True,  # Only if you have arbitrary types
    )

    # PUBLIC_INTERFACE
    def cors_origins_list(self) -> List[str]:
        """Return parsed CORS origins list from the CORS_ORIGINS string, handling '*' as wildcard."""
        value = (self.CORS_ORIGINS or "").strip()
        if value == "":
            return []
        if value == "*":
            return ["*"]
        return [o.strip() for o in value.split(",") if o.strip()]

    # PUBLIC_INTERFACE
    def cors_methods_list(self) -> List[str]:
        """Return parsed CORS methods list from CORS_METHODS, handling '*' as wildcard."""
        value = (self.CORS_METHODS or "").strip()
        if value == "":
            return []
        if value == "*":
            return ["*"]
        return [m.strip().upper() for m in value.split(",") if m.strip()]

    # PUBLIC_INTERFACE
    def cors_headers_list(self) -> List[str]:
        """Return parsed CORS headers list from CORS_HEADERS, handling '*' as wildcard."""
        value = (self.CORS_HEADERS or "").strip()
        if value == "":
            return []
        if value == "*":
            return ["*"]
        return [h.strip() for h in value.split(",") if h.strip()]

    # PUBLIC_INTERFACE
    def get_uvicorn_config(self) -> Tuple[str, int]:
        """Return (host, port) tuple for uvicorn from settings with safe defaults."""
        host = self.HOST or "0.0.0.0"
        try:
            port = int(self.PORT) if self.PORT else 3001
        except Exception:
            port = 3001
        return host, port


# PUBLIC_INTERFACE
def get_cors_origins(settings: "Settings") -> list[str]:
    """Parse comma-separated CORS origins into list."""
    return settings.cors_origins_list()


@lru_cache
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
