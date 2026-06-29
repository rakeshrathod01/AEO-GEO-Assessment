"""Module 9 — Leadership Dashboard: cross-module synthesis + prioritized roadmap.

Runs all eight modules at the requested scope, aggregates scores by layer, and
produces ONE prioritized roadmap sequenced **foundational SEO → AEO → GEO**.
Opus is used here (and only here) for the leadership synthesis / cross-module
prioritization; it degrades to deterministic ordering when no key is configured.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.analysis import AnalysisRun
from app.models.project import Project
from app.modules_registry import get_module
from app.schemas.contract import CompetitorDelta, ModuleResult
from app.schemas.leadership import (
    BenchmarkMarker,
    LeadershipReport,
    ModuleScore,
    RoadmapItem,
)
from app.services.analysis.base import status_from_score
from app.services.analysis.runner import AnalysisError, run_module_analysis
from app.services.benchmarks import list_benchmarks
from app.services.llm.client import LLMClient

MODULE = "leadership"
MODULES_ORDER = [
    "technical_seo", "on_page", "internal_linking", "backlinks", "keyword_universe",
    "aeo_audit", "prompt_identification", "geo_audit",
]
LAYER_ORDER = ["SEO", "AEO", "GEO"]
LAYER_WEIGHT = {"SEO": 0.5, "AEO": 0.25, "GEO": 0.25}  # foundational SEO weighted highest
_PRIORITY_RANK = {"high": 0, "med": 1, "low": 2}
_IMPACT_RANK = {"high": 0, "med": 1, "medium": 1, "low": 2, None: 3}


def _layer_of(key: str) -> str:
    meta = get_module(key)
    return meta.layer if meta else "SEO"


def _roadmap(results: dict[str, ModuleResult]) -> list[RoadmapItem]:
    items: list[RoadmapItem] = []
    order = 0
    for layer in LAYER_ORDER:
        layer_keys = [k for k in MODULES_ORDER if k in results and _layer_of(k) == layer]
        recs = [(k, r) for k in layer_keys for r in results[k].recommendations]
        recs.sort(key=lambda kr: (
            _PRIORITY_RANK.get(kr[1].priority.value, 3),
            _IMPACT_RANK.get(kr[1].impact, 3),
        ))
        seen: set[str] = set()
        for k, r in recs:
            if r.action in seen:  # dedup identical actions within a layer
                continue
            seen.add(r.action)
            order += 1
            items.append(RoadmapItem(
                phase=layer, order=order, priority=r.priority.value, layer=r.layer.value,
                module=k, action=r.action, how_to=r.how_to, effort=r.effort, impact=r.impact,
            ))
    return items


def _competitor_summary(results: dict[str, ModuleResult]) -> list[CompetitorDelta]:
    """Headline gaps where the client trails competitors (most-behind first)."""
    behind = []
    for res in results.values():
        for d in res.competitor_delta:
            if isinstance(d.gap, int | float) and d.gap < 0:
                behind.append(d)
    behind.sort(key=lambda d: d.gap)
    return behind[:10]


def _deterministic_summary(overall: int, layer_scores: dict, roadmap: list[RoadmapItem]) -> str:
    parts = [f"Overall readiness scores {overall}/100."]
    for layer in LAYER_ORDER:
        s = layer_scores.get(layer)
        if s is not None:
            parts.append(f"{layer} {s}/100.")
    top = [i.action for i in roadmap[:3]]
    if top:
        parts.append("Top priorities (foundational SEO first): " + "; ".join(top) + ".")
    return " ".join(parts)


def _opus_synthesis(llm: LLMClient, modules, roadmap, overall) -> tuple[str | None, dict]:
    if not llm.enabled:
        return None, {}
    system = (
        "You are a 20-year global SEO/AEO/GEO leader. Given module scores and a "
        "candidate roadmap, write a crisp executive summary and a one-line rationale "
        "per action. Keep the sequence foundational SEO first, then AEO, then GEO. "
        'Respond ONLY as JSON: {"executive_summary":"...","rationales":{"<action>":"<why>"}}'
    )
    payload = {
        "overall_score": overall,
        "modules": [{"title": m.title, "layer": m.layer, "score": m.score} for m in modules],
        "roadmap": [{"action": i.action, "layer": i.layer, "priority": i.priority}
                    for i in roadmap[:20]],
    }
    out = llm.synthesize_json(system, json.dumps(payload), max_tokens=1500)
    if not out:
        return None, {}
    return out.get("executive_summary"), out.get("rationales", {}) or {}


def run_leadership(
    db: Session, project_id: int, scope: str, page_id: int | None = None
) -> LeadershipReport:
    project = db.get(Project, project_id)
    if project is None:
        raise AnalysisError("Project not found")

    results: dict[str, ModuleResult] = {}
    for key in MODULES_ORDER:
        try:
            results[key] = run_module_analysis(db, project_id, key, scope, page_id)
        except AnalysisError:
            continue  # a module may be unavailable (e.g. no crawl yet) — skip it
    if not results:
        raise AnalysisError("No module results — run ingestion first")

    target_url = next(iter(results.values())).target_url

    modules = [
        ModuleScore(
            key=k, title=(get_module(k).title if get_module(k) else k),
            layer=_layer_of(k), score=res.score, status=res.status.value,
        )
        for k, res in results.items()
    ]

    # Layer + overall scores.
    layer_scores: dict[str, int | None] = {}
    for layer in LAYER_ORDER:
        scores = [m.score for m in modules if m.layer == layer]
        layer_scores[layer] = round(sum(scores) / len(scores)) if scores else None
    weighted = [(LAYER_WEIGHT[la], s) for la, s in layer_scores.items() if s is not None]
    overall = (
        round(sum(w * s for w, s in weighted) / sum(w for w, _ in weighted)) if weighted else 0
    )

    roadmap = _roadmap(results)
    llm = LLMClient(db)
    exec_summary, rationales = _opus_synthesis(llm, modules, roadmap, overall)
    synthesis_source = "opus" if exec_summary else "deterministic"
    if not exec_summary:
        exec_summary = _deterministic_summary(overall, layer_scores, roadmap)
    for item in roadmap:
        item.rationale = rationales.get(item.action)

    benchmarks = [
        BenchmarkMarker(metric=b["metric"], value=b["value"], unit=b["unit"],
                        source=b["source"], source_url=b["source_url"])
        for b in list_benchmarks(db)
    ]

    report = LeadershipReport(
        scope=scope, target_url=target_url, generated_at=utcnow().isoformat(),
        overall_score=overall, status=status_from_score(overall).value,
        layer_scores=layer_scores, modules=modules, executive_summary=exec_summary,
        roadmap=roadmap, benchmarks=benchmarks,
        competitor_summary=_competitor_summary(results),
        module_results=list(results.values()), synthesis_source=synthesis_source,
    )

    db.add(AnalysisRun(
        project_id=project_id, module=MODULE, scope=scope, target_url=target_url,
        score=overall, status=report.status, result_json=report.model_dump_json(),
    ))
    db.commit()
    return report
