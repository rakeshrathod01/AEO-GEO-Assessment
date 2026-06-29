import json
import os

from app.db.session import SessionLocal
from app.models.crawl import CrawlJob, Page
from app.models.project import Competitor, Project
from app.services.ingest.pipeline import run_ingestion


def _make_project_and_job():
    db = SessionLocal()
    try:
        project = Project(name="Acme", target_url="https://acme.com")
        project.competitors = [Competitor(name="Rival", url="https://rival.com")]
        db.add(project)
        db.commit()
        db.refresh(project)
        comp_id = project.competitors[0].id

        plan = {
            "client": {
                "mode": "paste",
                "urls": ["https://acme.com/", "https://acme.com/pricing"],
                "top_n": 50,
            },
            "competitors": [{"competitor_id": comp_id, "base_url": "https://rival.com"}],
        }
        job = CrawlJob(project_id=project.id, source_type="paste", input_json=json.dumps(plan))
        db.add(job)
        db.commit()
        db.refresh(job)
        return project.id, job.id, comp_id
    finally:
        db.close()


def test_pipeline_end_to_end(fake_fetcher):
    project_id, job_id, comp_id = _make_project_and_job()
    run_ingestion(job_id, fetcher=fake_fetcher)

    db = SessionLocal()
    try:
        job = db.get(CrawlJob, job_id)
        assert job.status == "done"
        assert job.total == 4  # 2 client + 2 mirrored competitor pages
        assert job.processed == 4

        pages = db.query(Page).filter(Page.crawl_job_id == job_id).all()
        client_pages = [p for p in pages if not p.is_competitor]
        comp_pages = [p for p in pages if p.is_competitor]
        assert len(client_pages) == 2
        assert len(comp_pages) == 2

        # Competitor pages mirror client paths and link back to the client page.
        comp_urls = {p.url for p in comp_pages}
        assert "https://rival.com/pricing" in comp_urls
        assert all(p.competitor_id == comp_id for p in comp_pages)
        assert all(p.matched_page_id is not None for p in comp_pages)

        # Extraction populated cleaned text + signals; raw HTML persisted to disk.
        sample = client_pages[0]
        assert sample.fetch_ok and sample.fetch_method == "fake"
        assert sample.cleaned_text and sample.word_count > 0
        assert sample.signals_json
        signals = json.loads(sample.signals_json)
        assert "has_canonical" in signals
        assert sample.raw_html_path and os.path.exists(sample.raw_html_path)
        assert sample.content_hash

        # Progress events were emitted.
        events = json.loads(job.events_json)
        assert events[-1]["status"] == "done"
        assert events[-1]["percent"] == 100
    finally:
        db.close()


def test_pipeline_ranks_and_caps_top_n(fake_fetcher):
    db = SessionLocal()
    try:
        project = Project(name="Big", target_url="https://big.com")
        db.add(project)
        db.commit()
        db.refresh(project)
        urls = [f"https://big.com/p{i}" for i in range(70)]
        plan = {"client": {"mode": "paste", "urls": urls, "top_n": 50}, "competitors": []}
        job = CrawlJob(project_id=project.id, source_type="paste", input_json=json.dumps(plan))
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    run_ingestion(job_id, fetcher=fake_fetcher)
    db = SessionLocal()
    try:
        job = db.get(CrawlJob, job_id)
        assert job.total == 50  # capped to top_n
        pages = db.query(Page).filter(Page.crawl_job_id == job_id).count()
        assert pages == 50
    finally:
        db.close()
