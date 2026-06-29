"""Module 8 — GEO Audit (site + page scope, with competitor_delta).

For each target prompt, queries every configured AI assistant (ChatGPT, Gemini,
Claude, Perplexity) and captures the Google AI Overview from the SERP, then
measures brand **mention / citation / position** for the client vs competitors,
per provider. Findings clearly flag whether a signal came from an **API** or
**SERP capture**.

The provider layer is swappable (see app/services/geo/providers.py); providers
are injected via the analysis context so the analyzer is data-source agnostic.
"""

from __future__ import annotations

import json

from app.core.config import settings
from app.models.geo import GeoResult
from app.models.project import Project
from app.models.prompt import Prompt
from app.schemas.contract import (
    CompetitorDelta,
    Layer,
    Priority,
    Recommendation,
    Status,
)
from app.services.analysis.base import Check, build_result
from app.services.geo.measure import detect, domain_of
from app.services.geo.providers import SOURCE_SERP
from app.services.prompts.generator import generate_prompts

MODULE = "geo_audit"


def _status(rate: float) -> Status:
    if rate >= 0.4:
        return Status.passing
    return Status.warn if rate >= 0.15 else Status.fail


def _load_prompts(db, project_id, target_url) -> list[Prompt]:
    prompts = db.query(Prompt).filter(Prompt.project_id == project_id).all()
    if not prompts:
        prompts = generate_prompts(db, project_id)
    return prompts


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    project = db.get(Project, ctx.project_id) if ctx.project_id else None
    client_brand = project.name if project else domain_of(ctx.target_url)
    client_domain = domain_of(ctx.target_url)
    competitors = [(name, domain_of(url)) for name, url in ctx.competitor_targets.items()]

    providers = ctx.geo_providers or []
    if not providers:
        check = Check(
            signal="geo_providers", status=Status.warn, weight=1.0, value="none",
            benchmark=None, source=None,
            evidence="No GEO providers configured — add OpenAI/Gemini/Anthropic/Perplexity "
                     "keys (API) or a Firecrawl key (SERP AI Overview capture) in Settings.",
        )
        return build_result(
            module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=[check],
            recommendations=[Recommendation(
                priority=Priority.high, layer=Layer.geo,
                action="Configure at least one GEO data source",
                how_to="Add an LLM API key or Firecrawl (for SERP AI Overview) in Settings.",
                effort="low", impact="high")],
            competitor_delta=[], generated_at=ctx.generated_at,
        )

    all_prompts = _load_prompts(db, ctx.project_id, ctx.target_url)
    prompts = all_prompts[: settings.GEO_MAX_PROMPTS]
    truncated = len(all_prompts) - len(prompts)

    # Clear prior results for this project+scope before recording fresh ones.
    db.query(GeoResult).filter(
        GeoResult.project_id == ctx.project_id, GeoResult.scope == ctx.scope
    ).delete()

    # Per-provider accumulators.
    agg: dict[str, dict] = {
        p.name: {"source_kind": p.source_kind, "n": 0, "mention": 0, "cited": 0,
                 "positions": [], "comp": {c[0]: {"mention": 0, "cited": 0} for c in competitors}}
        for p in providers
    }

    for prompt in prompts:
        for provider in providers:
            resp = provider.query(prompt.text)
            if not resp.ok:
                continue
            a = agg[provider.name]
            a["n"] += 1
            hit = detect(resp.text, resp.domains, client_brand, client_domain)
            a["mention"] += int(hit.mentioned)
            a["cited"] += int(hit.cited)
            if hit.position is not None:
                a["positions"].append(hit.position)

            comp_hits = []
            for cname, cdomain in competitors:
                ch = detect(resp.text, resp.domains, cname, cdomain)
                a["comp"][cname]["mention"] += int(ch.mentioned)
                a["comp"][cname]["cited"] += int(ch.cited)
                comp_hits.append({"name": cname, "mentioned": ch.mentioned,
                                  "cited": ch.cited, "position": ch.position})

            db.add(GeoResult(
                project_id=ctx.project_id, prompt_id=prompt.id, prompt_text=prompt.text,
                provider=provider.name, source_kind=provider.source_kind, scope=ctx.scope,
                client_mentioned=hit.mentioned, client_cited=hit.cited,
                client_position=hit.position, competitor_hits=json.dumps(comp_hits),
                response_excerpt=(resp.text or "")[:500],
            ))
    db.commit()

    # Build findings + competitor delta per provider.
    checks: list[Check] = []
    deltas: list[CompetitorDelta] = []
    citation_rates = []
    for provider in providers:
        a = agg[provider.name]
        n = a["n"]
        kind_label = "SERP capture" if provider.source_kind == SOURCE_SERP else "API"
        if n == 0:
            checks.append(Check(
                signal=f"{provider.name}_citation_rate", status=Status.warn, weight=1.0,
                value=0.0, benchmark=0.4, source=f"GEO data source: {kind_label}",
                evidence=f"[{kind_label}] no successful responses"))
            continue
        mention_rate = round(a["mention"] / n, 4)
        citation_rate = round(a["cited"] / n, 4)
        citation_rates.append(citation_rate)
        avg_pos = round(sum(a["positions"]) / len(a["positions"]), 2) if a["positions"] else None
        checks.append(Check(
            signal=f"{provider.name}_citation_rate", status=_status(citation_rate), weight=1.5,
            value=citation_rate, benchmark=0.4, source=f"GEO data source: {kind_label}",
            evidence=f"[{kind_label}] cited in {int(citation_rate*100)}% of {n} prompts; "
                     f"mentioned {int(mention_rate*100)}%; avg position {avg_pos}"))
        for cname, _ in competitors:
            them = round(a["comp"][cname]["cited"] / n, 4)
            deltas.append(CompetitorDelta(
                competitor=cname, signal=f"citation_rate@{provider.name}",
                us=citation_rate, them=them, gap=round(citation_rate - them, 4)))

    overall = round(sum(citation_rates) / len(citation_rates), 4) if citation_rates else 0.0
    checks.insert(0, Check(
        signal="geo_visibility", status=_status(overall), weight=2.0, value=overall,
        benchmark=0.4, source="eClerx GEO methodology — cross-assistant citation rate",
        evidence=(
            f"avg citation rate {int(overall*100)}% across {len(providers)} providers"
            + (f"; sampled {len(prompts)} of {len(all_prompts)} prompts" if truncated else "")
        )))

    recs: list[Recommendation] = []
    if overall < 0.4:
        recs.append(Recommendation(
            priority=Priority.high, layer=Layer.geo,
            action="Increase citation-worthiness for AI assistants",
            how_to="Publish concise, well-structured, citable answers with schema and strong "
                   "E-E-A-T so assistants surface and cite your pages.",
            effort="high", impact="high"))
    recs.append(Recommendation(
        priority=Priority.med, layer=Layer.geo,
        action="Build entity presence across the web",
        how_to="Strengthen Wikipedia/Wikidata, authoritative listings and consistent NAP so "
               "LLMs associate the brand with your topics.",
        effort="med", impact="high"))

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=checks,
        recommendations=recs, competitor_delta=deltas, generated_at=ctx.generated_at,
    )
