import json

from app.db.session import SessionLocal
from app.models.crawl import Page
from app.services.analysis import on_page, technical_seo
from app.services.analysis.eeat import detect_eeat
from app.services.analysis.runner import AnalysisContext


def _page(url, signals, cleaned_text="word " * 200, competitor=False):
    return Page(
        url=url,
        is_competitor=competitor,
        signals_json=json.dumps(signals),
        cleaned_text=cleaned_text,
        fetch_ok=True,
    )


def _good_tech_signals():
    return {
        "is_noindex": False, "has_viewport_meta": True, "has_canonical": True,
        "has_structured_data": True, "http_status": 200, "lang": "en",
    }


def _ctx(scope, client_pages, competitor_pages=None):
    db = SessionLocal()
    return AnalysisContext(
        db=db, scope=scope, target_url="https://acme.com",
        client_pages=client_pages, competitor_pages=competitor_pages or {}, llm=None,
    )


def test_technical_seo_contract_and_high_score():
    pages = [_page(f"https://acme.com/p{i}", _good_tech_signals()) for i in range(3)]
    ctx = _ctx("site", pages)
    try:
        result = technical_seo.analyze(ctx)
        assert result.module == "technical_seo"
        assert result.scope.value == "site"
        assert result.score >= 80
        assert result.status.value == "pass"
        # Every finding carries a cited source benchmark.
        assert all(f.source for f in result.findings)
    finally:
        ctx.db.close()


def test_technical_seo_flags_failures_and_recommends():
    bad = {
        "is_noindex": True, "has_viewport_meta": False, "has_canonical": False,
        "has_structured_data": False, "http_status": 500, "lang": None,
    }
    pages = [_page("http://acme.com/p", bad)]  # http (not https) too
    ctx = _ctx("site", pages)
    try:
        result = technical_seo.analyze(ctx)
        assert result.score < 50
        assert result.status.value == "fail"
        actions = {r.action for r in result.recommendations}
        assert any("HTTPS" in a for a in actions)
        assert any("noindex" in a.lower() for a in actions)
    finally:
        ctx.db.close()


def test_technical_competitor_delta():
    client = [_page("https://acme.com/p", _good_tech_signals())]
    comp_bad = {**_good_tech_signals(), "has_structured_data": False}
    competitors = {"Rival": [_page("https://rival.com/p", comp_bad, competitor=True)]}
    ctx = _ctx("site", client, competitors)
    try:
        result = technical_seo.analyze(ctx)
        sd = [d for d in result.competitor_delta if d.signal == "structured_data_rate"]
        assert sd and sd[0].competitor == "Rival"
        assert sd[0].us == 1.0 and sd[0].them == 0.0 and sd[0].gap == 1.0
    finally:
        ctx.db.close()


def test_on_page_contract_and_signals():
    sig = {
        "title": "Acme Pricing Plans For Teams", "title_length": 45,
        "meta_description": "x" * 120, "meta_description_length": 120,
        "h1_count": 1, "h2_count": 3, "word_count": 800,
        "images_count": 4, "images_missing_alt": 0,
        "og_title": "Acme", "has_structured_data": True, "external_links": 5,
    }
    text = "Written by Dr. Jane Smith, PhD. Updated 2024. According to research, ..."
    pages = [_page("https://acme.com/pricing", sig, cleaned_text=text)]
    ctx = _ctx("page", pages)
    try:
        result = on_page.analyze(ctx)
        assert result.module == "on_page"
        assert result.score >= 70
        signals_seen = {f.signal for f in result.findings}
        assert {"title_optimized", "schema_markup", "eeat", "content_depth"} <= signals_seen
    finally:
        ctx.db.close()


def test_on_page_thin_content_fails():
    sig = {
        "title": "Hi", "title_length": 2, "meta_description": None,
        "meta_description_length": 0, "h1_count": 0, "h2_count": 0,
        "word_count": 50, "images_count": 3, "images_missing_alt": 3,
        "og_title": None, "has_structured_data": False, "external_links": 0,
    }
    pages = [_page("https://acme.com/thin", sig, cleaned_text="short")]
    ctx = _ctx("page", pages)
    try:
        result = on_page.analyze(ctx)
        assert result.score < 50
        assert any(r.action for r in result.recommendations)
    finally:
        ctx.db.close()


def test_eeat_heuristic():
    strong = "Written by Dr. Smith, PhD. Published 2024. According to a study, trusted by customers."
    res = detect_eeat(strong, {"external_links": 5, "h1_count": 1, "h2_count": 2})
    assert res["flags"]["has_author"]
    assert res["flags"]["has_credentials"]
    assert res["flags"]["has_citations"]
    assert res["structure_ok"]
    assert res["score"] >= 0.8

    weak = detect_eeat("lorem ipsum", {"external_links": 0, "h1_count": 0, "h2_count": 0})
    assert weak["score"] < 0.4
    assert not weak["structure_ok"]
