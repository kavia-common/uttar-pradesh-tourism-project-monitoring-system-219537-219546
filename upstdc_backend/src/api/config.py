from functools import lru_cache
from typing import List, Optional
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables via pydantic-settings."""

    # App
    APP_NAME: str = "UPSTDC Project Monitoring API"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    SITE_URL: AnyUrl | None = None

    # CORS (comma-separated strings accepted for convenience)
    CORS_ORIGINS: str = "*"  # comma-separated list or '*'
    CORS_METHODS: str = "*"  # e.g. "GET,POST,PUT,DELETE,OPTIONS"
    CORS_HEADERS: str = "*"  # e.g. "Authorization,Content-Type"
    CORS_CREDENTIALS: bool = True

    # Mongo
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection string")
    MONGODB_DB: str = Field(default="upstdc", description="MongoDB database name")

    # JWT
    JWT_SECRET_KEY: str = Field(default="dev-secret-key-change-me", description="JWT secret key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Storage
    USE_LOCAL_STORAGE: bool = Field(default=False, description="If true, store uploads on local filesystem")
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

    # Rate limit
    RATE_LIMIT: str = "100/minute"

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host binding")
    PORT: int = Field(default=8000, description="Server port")

    # Accept and ignore unknown environment variables so startup doesn't fail on extras
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    # Backward compatibility for older pydantic-settings naming
    class Config:
        env_file = ".env"
        case_sensitive = True

    # PUBLIC_INTERFACE
    def cors_origins_list(self) -> List[str]:
        """Return parsed CORS origins list from the CORS_ORIGINS string, handling '*' as wildcard."""
        if not self.CORS_ORIGINS:
            return []
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # PUBLIC_INTERFACE
    def cors_methods_list(self) -> List[str]:
        """Return parsed CORS methods list from CORS_METHODS, handling '*' as wildcard."""
        if not self.CORS_METHODS:
            return []
        if self.CORS_METHODS.strip() == "*":
            return ["*"]
        return [m.strip().upper() for m in self.CORS_METHODS.split(",") if m.strip()]

    # PUBLIC_INTERFACE
    def cors_headers_list(self) -> List[str]:
        """Return parsed CORS headers list from CORS_HEADERS, handling '*' as wildcard."""
        if not self.CORS_HEADERS:
            return []
        if self.CORS_HEADERS.strip() == "*":
            return ["*"]
        return [h.strip() for h in self.CORS_HEADERS.split(",") if h.strip()]


# PUBLIC_INTERFACE
def get_cors_origins(settings: "Settings") -> list[str]:
    """Parse comma-separated CORS origins into list."""
    return settings.cors_origins_list()


@lru_cache
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
