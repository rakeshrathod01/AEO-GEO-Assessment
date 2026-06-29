import pytest
from pydantic import ValidationError

from app.schemas.contract import (
    CompetitorDelta,
    Finding,
    ModuleResult,
    Recommendation,
)


def test_module_result_minimal():
    res = ModuleResult(scope="page", target_url="https://example.com", score=82, status="pass")
    assert res.score == 82
    assert res.findings == []


def test_module_result_full_shape():
    res = ModuleResult(
        scope="site",
        target_url="https://example.com",
        score=64,
        status="warn",
        findings=[
            Finding(
                signal="lcp",
                status="warn",
                value=3.1,
                benchmark=2.5,
                source="Google CrUX 2024",
                evidence="LCP 3.1s on /home",
            )
        ],
        recommendations=[
            Recommendation(
                priority="high",
                layer="SEO",
                action="Optimize hero image",
                how_to="Serve AVIF + preload",
                effort="low",
                impact="high",
            )
        ],
        competitor_delta=[
            CompetitorDelta(competitor="acme.com", signal="lcp", them=2.1, us=3.1, gap=1.0)
        ],
    )
    assert res.findings[0].source == "Google CrUX 2024"
    assert res.recommendations[0].layer.value == "SEO"
    assert res.competitor_delta[0].gap == 1.0


def test_score_bounds_enforced():
    with pytest.raises(ValidationError):
        ModuleResult(scope="page", target_url="https://x.com", score=101, status="pass")


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        ModuleResult(scope="page", target_url="https://x.com", score=10, status="bogus")
