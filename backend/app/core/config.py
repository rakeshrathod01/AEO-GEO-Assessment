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

    # --- AI model tiering (cost control) ---
    # Haiku: extraction/classification. Sonnet: per-module analysis. Opus:
    # leadership synthesis only (Phase 6).
    MODEL_HAIKU: str = "claude-haiku-4-5"
    MODEL_SONNET: str = "claude-sonnet-4-6"
    MODEL_OPUS: str = "claude-opus-4-8"
    LLM_MAX_TOKENS: int = 2048
    # Cap cleaned text sent to the LLM (chars) — send cleaned text, never raw HTML.
    LLM_TEXT_CHAR_LIMIT: int = 12000

    # --- Prompt Identification (module 7) ---
    PROMPT_TARGET_COUNT: int = 65  # generate ~60-70 target prompts

    # --- GEO Audit (module 8) ---
    # Cap prompts queried per GEO run (cost control: prompts x providers calls).
    GEO_MAX_PROMPTS: int = 30

    # --- Auth / multi-tenancy ---
    # When False (local-first default) requests resolve to a shared "default"
    # tenant without a token. Set True in production to require JWT auth.
    AUTH_REQUIRED: bool = False
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # --- External-call rate limiting ---
    # Max external calls per provider per second (0 disables throttling).
    EXTERNAL_RATE_LIMIT_PER_SEC: float = 5.0

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
