"""Application configuration.

Local-first, cloud-ready: SQLite is the default store; set ``DATABASE_URL`` to a
Postgres DSN to swap with zero code changes. All secrets are read from the
environment — nothing is hardcoded.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    APP_NAME: str = "eClerx SEO/AEO/GEO Assessment Platform"
    APP_ENV: str = "local"  # local | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database (local-first SQLite; Postgres via env) ---
    # Examples:
    #   sqlite:///./eclerx_assessment.db
    #   postgresql+psycopg://user:pass@host:5432/eclerx
    DATABASE_URL: str = "sqlite:///./eclerx_assessment.db"

    # --- Celery / Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # --- Secrets ---
    # Master key used to derive the Fernet key that encrypts BYO API keys at rest.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    SECRET_KEY: str = "CHANGE-ME-dev-only-do-not-use-in-production"

    # --- CORS (frontend dev server) ---
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # --- External call cache ---
    # Default cache TTL (hours) for cached external API responses (Ahrefs, etc.).
    CACHE_TTL_HOURS: int = 24
    # Ahrefs pulls always use a trailing window of this many months.
    AHREFS_WINDOW_MONTHS: int = 6

    # --- Ingestion / crawler (Phase 1) ---
    # Directory where raw HTML is persisted to disk (cleaned text + signals go to DB).
    RAW_HTML_DIR: str = "./data/raw_html"
    # How many business-critical pages to select per site.
    TOP_N_PAGES: int = 50
    # Per-page fetch timeout (seconds).
    FETCH_TIMEOUT_SECONDS: int = 30
    # Below this many chars of cleaned text we treat a Firecrawl result as
    # bot-blocked / JS-heavy and fall back to Playwright-stealth.
    MIN_CONTENT_CHARS: int = 200
    # Run ingestion synchronously in-process instead of dispatching to Celery.
    # Default True for local-first dev (no Redis/worker required); set False in
    # production where a Celery worker consumes the queue.
    INGEST_INLINE: bool = True

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
