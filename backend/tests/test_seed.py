from app.db.session import SessionLocal
from app.models.crawl import STATUS_DONE, CrawlJob, Page
from app.models.project import Project
from app.models.tenant import User
from app.seed import DEMO_EMAIL, seed


def test_seed_is_idempotent_and_complete():
    db = SessionLocal()
    try:
        info = seed(db)
        assert info["email"] == DEMO_EMAIL

        # Demo user + project + completed crawl with client & competitor pages.
        assert db.query(User).filter(User.email == DEMO_EMAIL).count() == 1
        project = db.query(Project).filter(Project.name == "Acme Demo").one()
        job = db.query(CrawlJob).filter(
            CrawlJob.project_id == project.id, CrawlJob.status == STATUS_DONE
        ).one()
        client_pages = db.query(Page).filter(
            Page.crawl_job_id == job.id, Page.is_competitor.is_(False)
        ).count()
        comp_pages = db.query(Page).filter(
            Page.crawl_job_id == job.id, Page.is_competitor.is_(True)
        ).count()
        assert client_pages == 5
        assert comp_pages == 10  # 5 pages x 2 competitors

        # Re-running does not duplicate.
        seed(db)
        assert db.query(Project).filter(Project.name == "Acme Demo").count() == 1
        assert db.query(CrawlJob).filter(CrawlJob.project_id == project.id).count() == 1
    finally:
        db.close()


def test_seeded_project_runs_leadership():
    from app.services.analysis.leadership import run_leadership

    db = SessionLocal()
    try:
        info = seed(db)
        report = run_leadership(db, info["project_id"], "site")
        assert report.overall_score >= 0
        assert len(report.modules) >= 6  # most modules produce a score from the seed crawl
    finally:
        db.close()
