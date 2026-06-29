"""Cache for every external API call (Ahrefs, Firecrawl, LLM, ...).

Keyed by a deterministic hash of (provider, endpoint, params) so identical calls
are served from SQLite/Postgres instead of re-hitting paid APIs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ApiCache(Base, TimestampMixin):
    __tablename__ = "api_cache"

    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    request_params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    response_body: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
