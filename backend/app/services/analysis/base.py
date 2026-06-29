"""Shared builders for module analyzers: findings, scoring, competitor_delta.

Every analyzer composes these into a :class:`ModuleResult` (the data contract).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.contract import (
    CompetitorDelta,
    Finding,
    ModuleResult,
    Recommendation,
    Status,
)


@dataclass
class Check:
    """One evaluated signal: weight + pass/warn/fail + the value/benchmark/source."""

    signal: str
    status: Status
    weight: float
    value: object = None
    benchmark: object = None
    source: str | None = None
    evidence: str | None = None

    def to_finding(self) -> Finding:
        return Finding(
            signal=self.signal,
            status=self.status,
            value=self.value,
            benchmark=self.benchmark,
            source=self.source,
            evidence=self.evidence,
        )


# A pass earns full weight, a warn half, a fail none.
_STATUS_CREDIT = {Status.passing: 1.0, Status.warn: 0.5, Status.fail: 0.0}


def score_checks(checks: list[Check]) -> int:
    total_w = sum(c.weight for c in checks)
    if total_w <= 0:
        return 0
    earned = sum(_STATUS_CREDIT[c.status] * c.weight for c in checks)
    return round(earned / total_w * 100)


def status_from_score(score: int) -> Status:
    if score >= 80:
        return Status.passing
    if score >= 50:
        return Status.warn
    return Status.fail


def build_competitor_delta(
    client_metrics: dict[str, float],
    competitor_metrics: dict[str, dict[str, float]],
    signals: list[str],
) -> list[CompetitorDelta]:
    """Diff the client's headline metrics against each competitor's."""
    out: list[CompetitorDelta] = []
    for competitor, cm in competitor_metrics.items():
        for sig in signals:
            us = client_metrics.get(sig)
            them = cm.get(sig)
            gap: float | str | None = None
            if isinstance(us, int | float) and isinstance(them, int | float):
                gap = round(us - them, 4)
            out.append(
                CompetitorDelta(competitor=competitor, signal=sig, them=them, us=us, gap=gap)
            )
    return out


def maybe_enrich_recommendations(llm, recs: list[Recommendation]) -> list[Recommendation]:
    """Optionally upgrade recommendation how-to prose with Sonnet (analysis tier).

    No-ops (keeps deterministic static guidance) when no API key is configured.
    """
    if not recs or llm is None or not getattr(llm, "enabled", False):
        return recs
    import json

    actions = [{"i": i, "action": r.action} for i, r in enumerate(recs)]
    system = (
        "You are a senior technical SEO consultant. For each issue, write a concise, "
        "concrete how-to (1-2 sentences, imperative). Respond ONLY as JSON: "
        '{"items":[{"i":0,"how_to":"..."}]}'
    )
    out = llm.extract_json(system, json.dumps({"issues": actions}), max_tokens=1024)
    if not out or "items" not in out:
        return recs
    by_i = {item.get("i"): item.get("how_to") for item in out["items"] if "i" in item}
    for i, r in enumerate(recs):
        if by_i.get(i):
            r.how_to = by_i[i]
    return recs


def build_result(
    *,
    module: str,
    scope: str,
    target_url: str,
    checks: list[Check],
    recommendations: list[Recommendation],
    competitor_delta: list[CompetitorDelta],
    generated_at: str | None = None,
) -> ModuleResult:
    score = score_checks(checks)
    return ModuleResult(
        scope=scope,
        target_url=target_url,
        score=score,
        status=status_from_score(score),
        findings=[c.to_finding() for c in checks],
        recommendations=recommendations,
        competitor_delta=competitor_delta,
        module=module,
        generated_at=generated_at,
    )
