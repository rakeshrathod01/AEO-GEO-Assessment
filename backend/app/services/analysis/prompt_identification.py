"""Module 7 — Prompt Identification (site scope).

Generates ~60-70 target prompts across intent buckets (persisted), and returns a
data-contract summary scoring prompt volume + bucket diversity. The prompt list
itself is the deliverable (GET /projects/{id}/prompts and the prompts export).
"""

from __future__ import annotations

from app.core.config import settings
from app.models.prompt import INTENT_BUCKETS
from app.schemas.contract import Layer, Priority, Recommendation, Status
from app.services.analysis.base import Check, build_result
from app.services.prompts.generator import generate_prompts, prompts_by_bucket

MODULE = "prompt_identification"


def analyze(ctx) -> ModuleResult:  # noqa: F821
    db = ctx.db
    prompts = generate_prompts(db, ctx.project_id, target=settings.PROMPT_TARGET_COUNT)
    by_bucket = prompts_by_bucket(prompts)
    total = len(prompts)

    target = settings.PROMPT_TARGET_COUNT
    # Volume: aim for ~60-70; pass within 90% of target.
    if total >= target * 0.9:
        vol_status = Status.passing
    elif total >= target * 0.6:
        vol_status = Status.warn
    else:
        vol_status = Status.fail
    checks = [
        Check(
            signal="prompt_volume", status=vol_status, weight=1.5, value=total,
            benchmark=f"{target - 5}-{target + 5}",
            source="eClerx AEO/GEO methodology — target prompt set",
            evidence=f"{total} target prompts generated",
        )
    ]
    # Diversity: each bucket should carry a meaningful share.
    for bucket in INTENT_BUCKETS:
        count = len(by_bucket.get(bucket, []))
        status = Status.passing if count >= 5 else (Status.warn if count >= 2 else Status.fail)
        checks.append(Check(
            signal=f"bucket_{bucket}", status=status, weight=1.0, value=count,
            benchmark="≥5", source="eClerx AEO/GEO methodology — intent coverage",
            evidence=f"{count} {bucket} prompts",
        ))

    recs: list[Recommendation] = []
    for bucket in INTENT_BUCKETS:
        if len(by_bucket.get(bucket, [])) < 2:
            recs.append(Recommendation(
                priority=Priority.med, layer=Layer.geo,
                action=f"Expand {bucket} prompt coverage",
                how_to=f"Add content/keywords that surface more {bucket}-intent queries.",
                effort="med", impact="med"))

    return build_result(
        module=MODULE, scope=ctx.scope, target_url=ctx.target_url, checks=checks,
        recommendations=recs, competitor_delta=[], generated_at=ctx.generated_at,
    )
