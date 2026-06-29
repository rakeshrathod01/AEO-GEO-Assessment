import json

from app.db.session import SessionLocal
from app.models.crawl import Page
from app.services.analysis import backlinks, internal_linking, keyword_universe
from app.services.analysis.internal_graph import build_graph
from app.services.analysis.runner import AnalysisContext
from tests.conftest import FakeAhrefs


def _page(url, signals=None, competitor=False):
    return Page(
        url=url, is_competitor=competitor, fetch_ok=True,
        signals_json=json.dumps(signals or {"internal_links": 12}),
    )


def _ctx(scope="site", client_pages=None, competitor_pages=None, competitor_targets=None,
         ahrefs=None, project_id=1):
    db = SessionLocal()
    return AnalysisContext(
        db=db, scope=scope, target_url="https://acme.com",
        client_pages=client_pages or [_page("https://acme.com/")],
        competitor_pages=competitor_pages or {},
        competitor_targets=competitor_targets or {},
        project_id=project_id, llm=None, ahrefs=ahrefs,
    )


# --- internal link graph ---------------------------------------------------
def test_build_graph_detects_orphans_and_money_pages():
    pages = [
        ("https://acme.com/", "<a href='/pricing'>p</a><a href='/about'>a</a>"),
        ("https://acme.com/pricing", "<a href='/about'>a</a>"),
        ("https://acme.com/about", ""),
        ("https://acme.com/orphan", "<a href='/about'>a</a>"),
    ]
    g = build_graph(pages)
    assert g.inbound["https://acme.com/about"] == 3
    assert "https://acme.com/orphan" in g.orphans  # nothing links to it
    assert "https://acme.com/" in g.orphans  # homepage has no inbound in this set
    assert "https://acme.com/pricing" in g.money_pages


def test_internal_linking_analyzer(monkeypatch):
    # No raw HTML on disk -> falls back to signals for outbound.
    client = [_page(f"https://acme.com/p{i}", {"internal_links": 15}) for i in range(3)]
    competitors = {"Rival": [_page("https://rival.com/p", {"internal_links": 4}, True)]}
    ctx = _ctx(client_pages=client, competitor_pages=competitors)
    try:
        result = internal_linking.analyze(ctx)
        assert result.module == "internal_linking"
        delta = [d for d in result.competitor_delta if d.signal == "avg_internal_links"]
        assert delta and delta[0].us == 15 and delta[0].them == 4
    finally:
        ctx.db.close()


# --- backlinks -------------------------------------------------------------
def test_backlinks_with_ahrefs():
    ctx = _ctx(ahrefs=FakeAhrefs(dr=55), competitor_targets={"Rival": "https://rival.com"})
    try:
        result = backlinks.analyze(ctx)
        assert result.module == "backlinks"
        dr = [f for f in result.findings if f.signal == "domain_rating"][0]
        assert dr.value == 55
        delta = [d for d in result.competitor_delta if d.signal == "domain_rating"]
        assert delta and delta[0].them == 65 and delta[0].gap == -10  # competitor stronger
    finally:
        ctx.db.close()


def test_backlinks_degrades_without_ahrefs():
    ctx = _ctx(ahrefs=None)
    try:
        result = backlinks.analyze(ctx)
        assert any(f.signal == "ahrefs_data" for f in result.findings)
        assert any("Ahrefs" in r.action for r in result.recommendations)
    finally:
        ctx.db.close()


# --- keyword universe ------------------------------------------------------
def test_keyword_universe_persists_serp_queries():
    from app.models.project import Project
    from app.models.serp import SerpQuery

    db = SessionLocal()
    try:
        project = Project(name="Acme", target_url="https://acme.com")
        db.add(project)
        db.commit()
        pid = project.id
    finally:
        db.close()

    ctx = _ctx(ahrefs=FakeAhrefs(), competitor_targets={"Rival": "https://rival.com"},
               project_id=pid)
    try:
        result = keyword_universe.analyze(ctx)
        assert result.module == "keyword_universe"
        # gap exists because Rival ranks for "enterprise seo platform"
        gap = [f for f in result.findings if f.signal == "keyword_gaps"][0]
        assert gap.value >= 1

        rows = ctx.db.query(SerpQuery).filter(SerpQuery.project_id == pid).all()
        queries = {r.query for r in rows}
        assert "how to optimize seo" in queries
        paa = [r for r in rows if r.query_type == "paa"]
        assert paa and any(r.is_question for r in rows)
    finally:
        ctx.db.close()


def test_keyword_universe_dedupes_serp_queries():
    from app.models.project import Project
    from app.models.serp import SerpQuery

    db = SessionLocal()
    try:
        project = Project(name="Acme", target_url="https://acme.com")
        db.add(project)
        db.commit()
        pid = project.id
    finally:
        db.close()

    for _ in range(2):  # run twice -> no duplicates
        ctx = _ctx(ahrefs=FakeAhrefs(), project_id=pid)
        keyword_universe.analyze(ctx)
        ctx.db.close()

    db = SessionLocal()
    try:
        paa_for_kw = (
            db.query(SerpQuery)
            .filter(SerpQuery.project_id == pid, SerpQuery.query == "best seo tools")
            .all()
        )
        assert len(paa_for_kw) == 1
    finally:
        db.close()
