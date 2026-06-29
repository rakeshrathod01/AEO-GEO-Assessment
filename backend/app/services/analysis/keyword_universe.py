"""Module 5 — Keyword Universe analyzer (site + page scope, with competitor_delta).

Sources organic keywords from the Ahrefs MCP client (6-month window, cached):
totals, top-3/top-10 share, traffic, striking-distance (pos 4-10) opportunities,
SERP-feature coverage, and keyword gaps vs competitors.

Also persists PAA + featured-snippet (conversational) queries to ``serp_queries``
for Phase 5 (Prompt Identification / GEO).
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.serp import QUERY_FEATURED, QUERY_PAA, SerpQuery
from app.schemas.contract import Layer, Priority, Recommendation, Status
from app.services.analysis.base import (
    Check,
    build_competitor_delta,
    build_result,
    maybe_enrich_recommendations,
)
from app.services.benchmarks import get_benchmark

MODULE = "keyword_universe"
DELTA_SIGNALS = ["total_keywords", "total_traffic", "top10"]

_QUESTION_RE = re.compile(
    r"^(how|what|why|when|where|who|whose|whom|which|can|could|should|would|"
    r"do|does|did|is|are|will|may)\b",
    re.IGNORECASE,
)


def _is_question(text: str) -> bool:
    text = (text or "").strip()
    return text.endswith("?") or bool(_QUESTION_RE.match(text))


def _features(kw: dict) -> list[str]:
    feats = kw.get("serp_features") or kw.get("serp_feature") or []
    if isinstance(feats, str):
        feats = [feats]
    return [str(f).lower() for f in feats]


def _has_paa(feats: list[str]) -> bool:
    return any("paa" in f or "also_ask" in f or "also ask" in f for f in feats)


def _has_featured(feats: list[str]) -> bool:
    return any("featured" in f or "snippet" in f for f in feats)


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _metrics(keywords: list[dict]) -> dict[str, float]:
    positions = [_num(k.get("position")) for k in keywords if k.get("position") is not None]
    top3 = sum(1 for p in positions if 0 < p <= 3)
    top10 = sum(1 for p in positions if 0 < p <= 10)
    total = len(keywords)
    return {
        "total_keywords": total,
        "total_traffic": round(sum(_num(k.get("traffic")) for k in keywords), 2),
        "top3": top3,
        "top10": top10,
        "top10_share": round(top10 / total, 4) if total else 0.0,
        "striking_distance": sum(1 for p in positions if 4 <= p <= 10),
        "featured_snippets": sum(1 for k in keywords if _has_featured(_features(k))),
        "paa": sum(1 for k in keywords if _has_paa(_features(k))),
    }


def _persist_serp_queries(db: Session, project_id: int, keywords: list[dict]) -> int:
    """Upsert PAA + featured-snippet seeds for Phase 5. Returns rows written."""
    written = 0
    for k in keywords:
        kw = (k.get("keyword") or "").strip()
        if not kw:
            continue
        feats = _features(k)
        types = []
        if _has_paa(feats):
            types.append(QUERY_PAA)
        if _has_featured(feats):
            types.append(QUERY_FEATURED)
        for qtype in types:
            exists = (
                db.query(SerpQuery)
                .filter(
                    SerpQuery.project_id == project_id,
                    SerpQuery.query == kw,
                    SerpQuery.query_type == qtype,
                )
                .first()
            )
            if exists:
                continue
            db.add(SerpQuery(
                project_id=project_id, query=kw, query_type=qtype,
                seed_keyword=kw, is_question=_is_question(kw),
                volume=int(_num(k.get("volume"))) or None,
                difficulty=_num(k.get("difficulty")) or None,
                ranking_url=k.get("url"), source="ahrefs",
            ))
            written += 1
    if written:
        db.commit()
    return written


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    ahrefs = ctx.ahrefs
    keywords = ahrefs.organic_keywords(ctx.target_url) if ahrefs and ahrefs.enabled else []

    if not keywords:
        check = Check(
            signal="ahrefs_data", status=Status.warn, weight=1.0, value="unavailable",
            benchmark=None, source=None,
            evidence="Ahrefs MCP URL not configured — add it in Settings to populate keywords.",
        )
        return build_result(
            module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=[check],
            recommendations=[Recommendation(
                priority=Priority.high, layer=Layer.seo, action="Configure the Ahrefs MCP URL",
                how_to="Add the Ahrefs MCP URL in Settings to enable keyword analysis.",
                effort="low", impact="high")],
            competitor_delta=[], generated_at=ctx.generated_at,
        )

    m = _metrics(keywords)
    if ctx.project_id is not None:
        _persist_serp_queries(db, ctx.project_id, keywords)

    # Competitor keywords -> metrics + keyword-gap count.
    competitor_metrics: dict[str, dict] = {}
    client_kw_set = {(k.get("keyword") or "").lower() for k in keywords}
    total_gaps = 0
    if ahrefs and ahrefs.enabled:
        for name, target in ctx.competitor_targets.items():
            comp_kws = ahrefs.organic_keywords(target)
            competitor_metrics[name] = _metrics(comp_kws)
            comp_top = {
                (k.get("keyword") or "").lower()
                for k in comp_kws
                if 0 < _num(k.get("position")) <= 10
            }
            total_gaps += len(comp_top - client_kw_set)

    b_top10 = get_benchmark(db, "top10_share_min")
    b_strike = get_benchmark(db, "striking_distance")

    checks = [
        Check(signal="top10_share",
              status=Status.passing if m["top10_share"] >= 0.3 else (
                  Status.warn if m["top10_share"] >= 0.15 else Status.fail),
              weight=1.5, value=m["top10_share"], benchmark=b_top10.value if b_top10 else 0.3,
              source=b_top10.source if b_top10 else None,
              evidence=f"{m['top10']} of {m['total_keywords']} keywords in top 10"),
        Check(signal="total_keywords",
              status=Status.passing if m["total_keywords"] > 0 else Status.fail,
              weight=1.0, value=m["total_keywords"], benchmark=None,
              source=b_top10.source if b_top10 else None,
              evidence=f"{m['total_keywords']} ranking keywords"),
        Check(signal="striking_distance",
              status=Status.passing, weight=0.5, value=m["striking_distance"], benchmark=None,
              source=b_strike.source if b_strike else None,
              evidence=f"{m['striking_distance']} keywords in positions 4-10 (quick wins)"),
        Check(signal="serp_feature_coverage",
              status=Status.passing if (m["featured_snippets"] + m["paa"]) > 0 else Status.warn,
              weight=1.0, value=m["featured_snippets"] + m["paa"], benchmark=None, source=None,
              evidence=f"{m['featured_snippets']} featured snippets, {m['paa']} PAA SERPs"),
        Check(signal="keyword_gaps",
              status=Status.passing if total_gaps == 0 else (
                  Status.warn if total_gaps <= 50 else Status.fail),
              weight=1.0, value=total_gaps, benchmark=0, source=None,
              evidence=f"{total_gaps} keywords competitors rank for that the client does not"),
    ]

    recs: list[Recommendation] = []
    if m["top10_share"] < 0.3:
        recs.append(Recommendation(
            priority=Priority.high, layer=Layer.seo, action="Improve top-10 ranking share",
            how_to="Optimize on-page + internal links for high-intent terms outside the top 10.",
            effort="med", impact="high"))
    if m["striking_distance"] > 0:
        recs.append(Recommendation(
            priority=Priority.high, layer=Layer.seo, action="Capture striking-distance keywords",
            how_to="Refresh content + add internal links for positions 4-10 to reach the top 3.",
            effort="low", impact="high"))
    if total_gaps > 0:
        recs.append(Recommendation(
            priority=Priority.med, layer=Layer.seo, action="Close competitor keyword gaps",
            how_to="Create/optimize pages for high-value keywords only competitors rank for.",
            effort="high", impact="high"))
    if (m["featured_snippets"] + m["paa"]) > 0:
        recs.append(Recommendation(
            priority=Priority.med, layer=Layer.aeo, action="Win featured snippets & PAA",
            how_to="Add concise question-led answers and FAQ schema for PAA/snippet SERPs.",
            effort="med", impact="high"))
    recs = maybe_enrich_recommendations(ctx.llm, recs)

    delta = build_competitor_delta(m, competitor_metrics, DELTA_SIGNALS)

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=checks,
        recommendations=recs, competitor_delta=delta, generated_at=ctx.generated_at,
    )
