"""Leadership Dashboard (module 9) report schema."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.contract import CompetitorDelta, ModuleResult


class ModuleScore(BaseModel):
    key: str
    title: str
    layer: str  # SEO | AEO | GEO
    score: int
    status: str


class RoadmapItem(BaseModel):
    phase: str  # SEO | AEO | GEO (foundational SEO first)
    order: int
    priority: str
    layer: str
    module: str
    action: str
    how_to: str | None = None
    effort: str | None = None
    impact: str | None = None
    rationale: str | None = None


class BenchmarkMarker(BaseModel):
    metric: str
    value: float | None = None
    unit: str | None = None
    source: str  # citation string for the hover tooltip
    source_url: str | None = None


class LeadershipReport(BaseModel):
    scope: str
    target_url: str
    generated_at: str | None = None
    overall_score: int
    status: str
    layer_scores: dict[str, int | None]  # {"SEO":.., "AEO":.., "GEO":..}
    modules: list[ModuleScore]
    executive_summary: str
    roadmap: list[RoadmapItem]
    benchmarks: list[BenchmarkMarker]
    competitor_summary: list[CompetitorDelta] = []
    # Full per-module results (used by the master exports + dashboard drill-down).
    module_results: list[ModuleResult] = []
    synthesis_source: str = "deterministic"  # "opus" | "deterministic"
