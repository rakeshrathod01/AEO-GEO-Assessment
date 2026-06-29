"""SERP conversational queries (PAA + featured snippets).

Pulled during the Keyword Universe module (Phase 3) and consumed by Phase 5
(Prompt Identification / GEO) — these question-shaped queries are the seeds for
AI-assistant prompt targeting.
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

QUERY_PAA = "paa"
QUERY_FEATURED = "featured_snippet"


class SerpQuery(Base, TimestampMixin):
    __tablename__ = "serp_queries"
    __table_args__ = (
        UniqueConstraint("project_id", "query", "query_type", name="uq_serp_project_query_type"),
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    query: Mapped[str] = mapped_column(String(512), nullable=False)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False)  # paa | featured_snippet
    seed_keyword: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_question: Mapped[bool] = mapped_column(default=False, index=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="ahrefs")
