from app.db.session import SessionLocal
from app.models.geo import GeoResult
from app.models.project import Competitor, Project
from app.services.analysis.geo_audit import analyze
from app.services.analysis.runner import AnalysisContext
from app.services.geo.measure import detect, domain_of
from app.services.geo.providers import build_providers, extract_domains
from tests.conftest import FakeGeoProvider, fake_geo_providers


def test_extract_domains():
    doms = extract_domains("see https://www.Acme.com/x and http://rival.com", ["https://foo.com/a"])
    assert doms[0] == "foo.com"
    assert "acme.com" in doms and "rival.com" in doms


def test_measure_detect():
    hit = detect("Acme is great", ["acme.com", "rival.com"], "Acme", "acme.com")
    assert hit.mentioned and hit.cited and hit.position == 1
    miss = detect("nothing here", ["other.com"], "Acme", "acme.com")
    assert not miss.mentioned and not miss.cited and miss.position is None


def test_build_providers_empty_without_keys():
    db = SessionLocal()
    try:
        assert build_providers(db) == []
    finally:
        db.close()


def _project():
    db = SessionLocal()
    try:
        p = Project(name="Acme", target_url="https://acme.com", industry="SEO")
        p.competitors = [Competitor(name="Rival", url="https://rival.com")]
        db.add(p)
        db.commit()
        return p.id
    finally:
        db.close()


def test_geo_audit_with_fake_providers():
    pid = _project()
    db = SessionLocal()
    ctx = AnalysisContext(
        db=db, scope="site", target_url="https://acme.com", client_pages=[],
        competitor_targets={"Rival": "https://rival.com"}, project_id=pid, llm=None,
        geo_providers=fake_geo_providers(),
    )
    try:
        result = analyze(ctx)
        assert result.module == "geo_audit"
        # Overall + per-provider citation findings; SERP source flagged.
        signals = {f.signal for f in result.findings}
        assert "geo_visibility" in signals
        assert "chatgpt_citation_rate" in signals
        serp = [f for f in result.findings if f.signal == "ai_overview_citation_rate"][0]
        assert "SERP capture" in serp.evidence
        api = [f for f in result.findings if f.signal == "chatgpt_citation_rate"][0]
        assert "API" in api.evidence
        # Client cited every prompt -> high citation rate.
        assert api.value == 1.0
        # Competitor delta present (Rival cited by chatgpt fake, not by serp fake).
        assert any(d.signal.startswith("citation_rate@") for d in result.competitor_delta)
        # Results persisted with source kinds.
        kinds = {r.source_kind for r in db.query(GeoResult).filter(GeoResult.project_id == pid)}
        assert kinds == {"api", "serp"}
    finally:
        db.close()


def test_geo_audit_degrades_without_providers():
    pid = _project()
    db = SessionLocal()
    ctx = AnalysisContext(
        db=db, scope="site", target_url="https://acme.com", client_pages=[],
        project_id=pid, llm=None, geo_providers=[],
    )
    try:
        result = analyze(ctx)
        assert any(f.signal == "geo_providers" for f in result.findings)
        assert any("data source" in r.action.lower() for r in result.recommendations)
    finally:
        db.close()


def test_geo_position_from_domain_order():
    hit = detect("text", ["rival.com", "acme.com"], "Acme", "acme.com")
    assert hit.position == 2  # client cited second
    assert domain_of("https://www.acme.com/path") == "acme.com"
    _ = FakeGeoProvider  # imported for fixture parity
