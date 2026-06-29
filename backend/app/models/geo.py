"""GEO Audit results (module 8): one row per (prompt, provider).

Records whether the client brand was mentioned/cited and at what position in the
AI assistant's answer (or the SERP AI Overview), plus the same for competitors.
``source_kind`` flags whether signals came from an LLM API or SERP capture.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SOURCE_API = "api"
SOURCE_SERP = "serp"


class GeoResult(Base, TimestampMixin):
    __tablename__ = "geo_results"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    prompt_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(8), nullable=False)  # api | serp
    scope: Mapped[str] = mapped_column(String(8), default="site")

    client_mentioned: Mapped[bool] = mapped_column(default=False)
    client_cited: Mapped[bool] = mapped_column(default=False)
    client_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # [{name, mentioned, cited, position}] for each competitor.
    competitor_hits: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
