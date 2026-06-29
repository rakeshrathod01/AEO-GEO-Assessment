"""The shared DATA CONTRACT.

Every analysis module — at both ``site`` and ``page`` scope — returns a
:class:`ModuleResult`. Keeping this in one place guarantees deterministic,
structured output across the whole platform and makes exports/reports uniform.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Scope(str, Enum):
    site = "site"
    page = "page"


class Status(str, Enum):
    passing = "pass"
    warn = "warn"
    fail = "fail"


class Priority(str, Enum):
    high = "high"
    med = "med"
    low = "low"


class Layer(str, Enum):
    seo = "SEO"
    aeo = "AEO"
    geo = "GEO"


class Finding(BaseModel):
    signal: str
    status: Status
    value: str | float | int | bool | None = None
    benchmark: str | float | int | None = None
    source: str | None = Field(
        default=None, description="Citation for the benchmark (see benchmark_sources)."
    )
    evidence: str | None = None


class Recommendation(BaseModel):
    priority: Priority
    layer: Layer
    action: str
    how_to: str | None = None
    effort: str | None = Field(default=None, description="e.g. low | medium | high")
    impact: str | None = Field(default=None, description="e.g. low | medium | high")


class CompetitorDelta(BaseModel):
    competitor: str
    signal: str
    them: str | float | int | None = None
    us: str | float | int | None = None
    gap: str | float | int | None = None


class ModuleResult(BaseModel):
    """The single shape returned by every module."""

    scope: Scope
    target_url: HttpUrl | str
    score: int = Field(ge=0, le=100)
    status: Status
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    competitor_delta: list[CompetitorDelta] = Field(default_factory=list)

    # Non-contract metadata (handy for persistence/exports; ignored by validators).
    module: str | None = None
    generated_at: str | None = None
