from app.db.session import SessionLocal
from app.models.project import Competitor, Project
from app.models.prompt import INTENT_BUCKETS, Prompt
from app.services.analysis.prompt_identification import analyze
from app.services.analysis.runner import AnalysisContext
from app.services.prompts.generator import classify_intent, generate_prompts


def test_classify_intent():
    assert classify_intent("acme vs rival") == "comparison"
    assert classify_intent("acme pricing") == "transactional"
    assert classify_intent("best seo tools") == "commercial"
    assert classify_intent("acme login") == "navigational"
    assert classify_intent("how does seo work") == "informational"


def _project():
    """Project with realistic seeds: competitors + SERP queries (as the keyword
    module would persist), so prompt generation has enough topic material."""
    from app.models.serp import SerpQuery

    db = SessionLocal()
    try:
        p = Project(name="Acme", target_url="https://acme.com", industry="SEO software")
        p.competitors = [Competitor(name="Rival", url="https://rival.com"),
                         Competitor(name="Foo", url="https://foo.com")]
        db.add(p)
        db.commit()
        seeds = ["link building", "keyword research", "rank tracking", "site audit",
                 "content optimization", "backlink analysis"]
        for kw in seeds:
            db.add(SerpQuery(project_id=p.id, query=f"how to do {kw}", query_type="paa",
                             seed_keyword=kw, is_question=True))
        db.commit()
        return p.id
    finally:
        db.close()


def test_generate_prompts_hits_target_and_buckets():
    pid = _project()
    db = SessionLocal()
    try:
        prompts = generate_prompts(db, pid, target=65)
        assert 55 <= len(prompts) <= 65
        buckets = {p.intent_bucket for p in prompts}
        # All five intent buckets represented.
        assert set(INTENT_BUCKETS) <= buckets
        # Comparison prompts reference competitors.
        assert any("Rival" in p.text for p in prompts)
    finally:
        db.close()


def test_generate_prompts_replaces_on_rerun():
    pid = _project()
    db = SessionLocal()
    try:
        generate_prompts(db, pid, target=65)
        generate_prompts(db, pid, target=65)
        count = db.query(Prompt).filter(Prompt.project_id == pid).count()
        assert 55 <= count <= 65  # replaced, not duplicated
    finally:
        db.close()


def test_prompt_identification_analyzer_contract():
    pid = _project()
    db = SessionLocal()
    ctx = AnalysisContext(
        db=db, scope="site", target_url="https://acme.com", client_pages=[],
        project_id=pid, llm=None,
    )
    try:
        result = analyze(ctx)
        assert result.module == "prompt_identification"
        vol = [f for f in result.findings if f.signal == "prompt_volume"][0]
        assert vol.value >= 55
        assert result.score >= 60
    finally:
        db.close()
