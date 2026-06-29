"""Ingestion/crawl models.

A :class:`CrawlJob` is one ingestion run for a project (client + competitors).
Each crawled :class:`Page` stores cleaned text + extracted signals in the DB;
the raw HTML lives on disk (``raw_html_path``).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# Source of the URL list for an ingestion run.
SOURCE_SITEMAP = "sitemap"
SOURCE_EXCEL = "excel"
SOURCE_PASTE = "paste"

# Job lifecycle.
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


class CrawlJob(Base, TimestampMixin):
    __tablename__ = "crawl_jobs"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # sitemap|excel|paste
    status: Mapped[str] = mapped_column(String(16), default=STATUS_PENDING, index=True)

    # Normalized ingestion plan (client URLs/sitemap + competitor specs), JSON string.
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Progress stream snapshot.
    total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Rolling list of progress events (JSON string) for replay into the UI.
    events_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    pages: Mapped[list[Page]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def percent(self) -> int:
        if not self.total:
            return 0
        return min(100, round(self.processed / self.total * 100))


class Page(Base, TimestampMixin):
    __tablename__ = "pages"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    crawl_job_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"), index=True
    )
    # NULL = client target page; set = a competitor's page.
    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # For competitor pages: the client Page this one is the comparable of.
    matched_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("pages.id", ondelete="SET NULL"), nullable=True
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    is_competitor: Mapped[bool] = mapped_column(default=False, index=True)

    # Ranking outcome.
    rank_score: Mapped[float | None] = mapped_column(nullable=True)
    rank_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    selected: Mapped[bool] = mapped_column(default=True, index=True)

    # Fetch outcome. fetch_method is "firecrawl" or "playwright".
    fetch_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetch_ok: Mapped[bool] = mapped_column(default=False)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Cleaned content + a few hot columns mirrored from signals for fast queries.
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full extracted on-page + technical signal bundle (JSON string).
    signals_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[CrawlJob] = relationship(back_populates="pages")
