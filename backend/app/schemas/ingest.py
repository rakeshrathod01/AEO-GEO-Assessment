"""Ingestion request/response schemas for the three input modes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompetitorSitemapSpec(BaseModel):
    competitor_id: int | None = None
    base_url: str | None = None  # mirror client paths onto this domain
    sitemap_url: str | None = None  # or rank+match the competitor's own sitemap


class SitemapIngestIn(BaseModel):
    sitemap_url: str
    top_n: int = Field(default=50, ge=1, le=200)
    competitors: list[CompetitorSitemapSpec] = []


class CompetitorUrlsSpec(BaseModel):
    competitor_id: int | None = None
    base_url: str | None = None
    urls: list[str] | None = None


class PasteIngestIn(BaseModel):
    text: str = Field(description="Pasted URLs (newline/comma/space separated).")
    top_n: int = Field(default=50, ge=1, le=200)
    competitors: list[CompetitorUrlsSpec] = []


class JobOut(BaseModel):
    id: int
    project_id: int
    source_type: str
    status: str
    total: int
    processed: int
    percent: int
    message: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class PageOut(BaseModel):
    id: int
    url: str
    is_competitor: bool
    competitor_id: int | None = None
    matched_page_id: int | None = None
    rank_score: float | None = None
    selected: bool
    fetch_method: str | None = None
    http_status: int | None = None
    fetch_ok: bool
    title: str | None = None
    meta_description: str | None = None
    word_count: int | None = None
