import json

from app.db.session import SessionLocal
from app.models.crawl import Page
from app.models.project import Project
from app.models.serp import SerpQuery
from app.services.analysis import aeo_audit
from app.services.analysis.aeo_features import extract_aeo_features
from app.services.analysis.runner import AnalysisContext

STRONG_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"FAQPage"}</script>
<script type="application/ld+json">
{"@type":["Organization"]}</script>
<script type="application/ld+json">
{"@type":"SpeakableSpecification"}</script>
</head><body>
<h1>SEO Guide</h1>
<p>Answer engine optimization means structuring content so AI assistants can
quote it directly, using concise answers, clear headings and schema markup today.</p>
<h2>What is answer engine optimization?</h2>
<p>It is the practice of optimizing for AI answers.</p>
<ul><li>one</li><li>two</li></ul>
<table><tr><td>x</td></tr></table>
</body></html>
"""

WEAK_HTML = "<html><body><h2>Our products</h2><p>Buy now.</p></body></html>"


def test_extract_features_strong():
    f = extract_aeo_features(STRONG_HTML)
    assert f["question_headings"] == 1
    assert f["has_concise_answer"] is True
    assert f["has_faq_schema"] and f["has_org_schema"] and f["has_speakable"]
    assert f["lists"] == 1 and f["tables"] == 1


def test_extract_features_weak():
    f = extract_aeo_features(WEAK_HTML)
    assert f["question_headings"] == 0
    assert not f["has_faq_schema"]
    assert not f["has_speakable"]


def _page(tmp_path, idx, html, *, competitor=False, cleaned_text=""):
    path = tmp_path / f"page_{idx}.html"
    path.write_text(html, encoding="utf-8")
    return Page(
        url=f"https://acme.com/p{idx}", is_competitor=competitor, fetch_ok=True,
        raw_html_path=str(path), cleaned_text=cleaned_text, signals_json=json.dumps({}),
    )


def _ctx(client_pages, competitor_pages=None, project_id=None):
    db = SessionLocal()
    return AnalysisContext(
        db=db, scope="site", target_url="https://acme.com",
        client_pages=client_pages, competitor_pages=competitor_pages or {},
        project_id=project_id, llm=None, ahrefs=None,
    )


def test_aeo_analyzer_strong_vs_weak_competitor(tmp_path):
    client = [_page(tmp_path, i, STRONG_HTML) for i in range(2)]
    competitors = {"Rival": [_page(tmp_path, 100 + i, WEAK_HTML, competitor=True) for i in range(2)]}
    ctx = _ctx(client, competitors)
    try:
        result = aeo_audit.analyze(ctx)
        assert result.module == "aeo_audit"
        signals = {f.signal for f in result.findings}
        assert {
            "ai_overview_readiness", "people_also_ask_readiness", "knowledge_panel_readiness",
            "voice_search_readiness", "answer_paragraph_readiness", "content_structure_readiness",
        } == signals
        assert all(f.source for f in result.findings)  # cited benchmarks
        assert result.score >= 60

        faq = [d for d in result.competitor_delta if d.signal == "faq_schema_rate"][0]
        assert faq.us == 1.0 and faq.them == 0.0 and faq.gap == 1.0
    finally:
        ctx.db.close()


def test_aeo_weak_site_recommends(tmp_path):
    client = [_page(tmp_path, i, WEAK_HTML) for i in range(2)]
    ctx = _ctx(client)
    try:
        result = aeo_audit.analyze(ctx)
        assert result.score < 50
        layers = {r.layer.value for r in result.recommendations}
        assert layers == {"AEO"}
        assert any("schema" in (r.how_to or "").lower() for r in result.recommendations)
    finally:
        ctx.db.close()


def test_aeo_paa_coverage_uses_serp_queries(tmp_path):
    db = SessionLocal()
    try:
        project = Project(name="Acme", target_url="https://acme.com")
        db.add(project)
        db.commit()
        pid = project.id
        db.add_all([
            SerpQuery(project_id=pid, query="how to optimize seo", query_type="paa",
                      is_question=True),
            SerpQuery(project_id=pid, query="what is link building", query_type="paa",
                      is_question=True),
        ])
        db.commit()
    finally:
        db.close()

    # One client page whose text addresses the first PAA query only.
    page = _page(tmp_path, 1, STRONG_HTML,
                 cleaned_text="Here is how to optimize seo with concise answers and schema.")
    ctx = _ctx([page], project_id=pid)
    try:
        result = aeo_audit.analyze(ctx)
        paa = [f for f in result.findings if f.signal == "people_also_ask_readiness"][0]
        assert "1/2" in paa.evidence  # one of two PAA queries addressed
    finally:
        ctx.db.close()
