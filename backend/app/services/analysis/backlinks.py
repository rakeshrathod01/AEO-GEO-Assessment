"""Module 4 — Backlinks analyzer (site + page scope, with competitor_delta).

Sources data from the Ahrefs MCP client (6-month window, cached): Domain Rating,
referring domains, total backlinks, and dofollow ratio. Degrades to a single
"configure Ahrefs" finding when no MCP URL is set.
"""

from __future__ import annotations

from app.schemas.contract import Layer, Priority, Recommendation, Status
from app.services.analysis.base import (
    Check,
    build_competitor_delta,
    build_result,
    maybe_enrich_recommendations,
)
from app.services.benchmarks import get_benchmark

MODULE = "backlinks"
DELTA_SIGNALS = ["domain_rating", "referring_domains", "backlinks"]


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _metrics(stats: dict | None) -> dict[str, float]:
    stats = stats or {}
    return {
        "domain_rating": _num(stats.get("domain_rating")),
        "referring_domains": _num(stats.get("referring_domains")),
        "backlinks": _num(stats.get("backlinks")),
        "dofollow_ratio": _num(stats.get("dofollow_ratio")),
    }


def _status_min(value, minimum) -> Status:
    if value >= minimum:
        return Status.passing
    return Status.warn if value >= minimum * 0.5 else Status.fail


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    ahrefs = ctx.ahrefs
    stats = ahrefs.backlinks_stats(ctx.target_url) if ahrefs and ahrefs.enabled else None

    if not stats:
        check = Check(
            signal="ahrefs_data", status=Status.warn, weight=1.0,
            value="unavailable", benchmark=None, source=None,
            evidence="Ahrefs MCP URL not configured — add it in Settings to populate backlinks.",
        )
        return build_result(
            module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=[check],
            recommendations=[Recommendation(
                priority=Priority.high, layer=Layer.seo,
                action="Configure the Ahrefs MCP URL",
                how_to="Add the Ahrefs MCP URL in Settings to enable backlink analysis.",
                effort="low", impact="high")],
            competitor_delta=[], generated_at=ctx.generated_at,
        )

    m = _metrics(stats)
    b_dr = get_benchmark(db, "domain_rating_min")
    b_rd = get_benchmark(db, "referring_domains_min")
    b_df = get_benchmark(db, "dofollow_ratio_min")

    checks = [
        Check(signal="domain_rating", status=_status_min(m["domain_rating"], 40), weight=1.5,
              value=m["domain_rating"], benchmark=b_dr.value if b_dr else 40,
              source=b_dr.source if b_dr else None, evidence=f"DR {m['domain_rating']}"),
        Check(signal="referring_domains", status=_status_min(m["referring_domains"], 100),
              weight=1.5, value=m["referring_domains"], benchmark=b_rd.value if b_rd else 100,
              source=b_rd.source if b_rd else None,
              evidence=f"{int(m['referring_domains'])} referring domains"),
        Check(signal="dofollow_ratio", status=_status_min(m["dofollow_ratio"], 0.5), weight=1.0,
              value=m["dofollow_ratio"], benchmark=b_df.value if b_df else 0.5,
              source=b_df.source if b_df else None,
              evidence=f"{round(m['dofollow_ratio'] * 100)}% dofollow"),
        Check(signal="total_backlinks",
              status=Status.passing if m["backlinks"] > 0 else Status.warn,
              weight=0.5, value=m["backlinks"], benchmark=None,
              source=b_rd.source if b_rd else None, evidence=f"{int(m['backlinks'])} backlinks"),
    ]

    recs: list[Recommendation] = []
    for c in checks:
        if c.status == Status.passing:
            continue
        if c.signal == "domain_rating":
            recs.append(Recommendation(
                priority=Priority.high, layer=Layer.seo, action="Grow Domain Rating",
                how_to="Earn links from higher-DR, relevant sites via digital PR and content.",
                effort="high", impact="high"))
        elif c.signal == "referring_domains":
            recs.append(Recommendation(
                priority=Priority.high, layer=Layer.seo, action="Acquire more referring domains",
                how_to="Prioritize new unique linking domains over more links from existing ones.",
                effort="high", impact="high"))
        elif c.signal == "dofollow_ratio":
            recs.append(Recommendation(
                priority=Priority.med, layer=Layer.seo, action="Improve dofollow link share",
                how_to="Pursue editorial dofollow placements; audit for excessive nofollow.",
                effort="med", impact="med"))
    recs = maybe_enrich_recommendations(ctx.llm, recs)

    competitor_metrics = {}
    if ahrefs and ahrefs.enabled:
        for name, target in ctx.competitor_targets.items():
            competitor_metrics[name] = _metrics(ahrefs.backlinks_stats(target))
    delta = build_competitor_delta(m, competitor_metrics, DELTA_SIGNALS)

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=checks,
        recommendations=recs, competitor_delta=delta, generated_at=ctx.generated_at,
    )
