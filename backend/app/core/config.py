"""Application settings, loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "MetroCheck"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[2] / 'app.db').as_posix()}"
    redis_url: str = "redis://localhost:6379/0"

    # Gemini is optional: without a key MetroCheck degrades to OCR extraction.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    secret_key: str = "dev_only_secret_change_me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    upload_dir: str = "uploads"
    reports_dir: str = "generated_reports"
    max_upload_size_mb: int = 20

    # Comma separated list of allowed browser origins.
    cors_origins: str = "http://localhost:3000"

    # Run Alembic migrations automatically on container start.
    run_migrations: bool = False

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        return self._resolve(self.upload_dir)

    @property
    def reports_path(self) -> Path:
        return self._resolve(self.reports_dir)

    @staticmethod
    def _resolve(directory: str) -> Path:
        """Resolve a configured directory relative to the backend root."""
        path = Path(directory)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
