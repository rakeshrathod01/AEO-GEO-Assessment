"""Industry benchmarks always carry a cited source.

Sources are persisted here and reused across modules/reports — never re-derived.
"""

from __future__ import annotations

from sqlalchemy import Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BenchmarkSource(Base, TimestampMixin):
    __tablename__ = "benchmark_sources"
    __table_args__ = (
        UniqueConstraint("metric", "industry", name="uq_benchmark_metric_industry"),
    )

    # e.g. "core_web_vitals.lcp", "organic_ctr.position_1"
    metric: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Citation — required so every benchmark is defensible in client deliverables.
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_year: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
