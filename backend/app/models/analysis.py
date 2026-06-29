"""Persisted results of a module analysis run (conforms to the data contract)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_runs"

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # One of the 9 modules: technical_seo, on_page, internal_linking, backlinks,
    # keyword_universe, aeo_audit, prompt_identification, geo_audit, leadership.
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(8), nullable=False)  # site | page
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(8), nullable=True)  # pass|warn|fail

    # Full ModuleResult payload, serialized as JSON (works on SQLite + Postgres).
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
