"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration. Reads from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_name: str = "JobPair.aloe"
    app_version: str = "1.0.0"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"

    # CORS
    frontend_url: str = "http://localhost:3000"
    allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # Database
    # DATABASE_URL is the async DSN (asyncpg); DATABASE_URL_SYNC is the
    # sync DSN used by Alembic.
    #
    # We deliberately do NOT ship a working default. The placeholder
    # below points at host `localhost` with credentials `<set-in-env>`
    # so it can never accidentally connect anywhere. Set real values
    # in .env (see .env.example) or docker-compose will refuse to start.
    database_url: str = (
        "postgresql+asyncpg://<set-in-env>:<set-in-env>@localhost:5432/<set-in-env>"
    )
    database_url_sync: str = (
        "postgresql://<set-in-env>:<set-in-env>@localhost:5432/<set-in-env>"
    )

    # File upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    allowed_extensions: List[str] = Field(default_factory=lambda: [".pdf"])

    # ML
    ml_model_dir: str = "./ml_models"
    sklearn_model_path: str = "./ml_models/sklearn_baseline.joblib"
    pytorch_model_path: str = "./ml_models/pytorch_matcher.pt"
    training_data_path: str = "./ml_models/training_data.json"

    # Logging
    log_level: str = "INFO"

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ml_path(self) -> Path:
        path = Path(self.ml_model_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
