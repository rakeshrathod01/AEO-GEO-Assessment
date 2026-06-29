"""Idempotent seed / demo dataset.

Creates a demo tenant + admin user, a demo project with competitors, and a
completed synthetic crawl (client + matched competitor pages with real extracted
signals) so every module + the leadership dashboard run immediately — no live
crawl or API keys required.

Run:  python -m app.seed
"""

from __future__ import annotations

from app.core.auth import hash_password
from app.db.session import SessionLocal
from app.models.crawl import SOURCE_PASTE, STATUS_DONE, CrawlJob, Page
from app.models.project import Competitor, Project
from app.models.tenant import ROLE_ADMIN, Tenant, User
from app.services.benchmarks import seed_default_benchmarks
from app.services.ingest.extract import extract
from app.services.ingest.storage import content_hash, save_raw_html

DEMO_TENANT_SLUG = "demo"
DEMO_EMAIL = "demo@eclerx.com"
DEMO_PASSWORD = "demo-password"

_PAGE_HTML = """
<html lang="en"><head>
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{{"@type":"{schema}"}}</script>
</head><body>
<h1>{h1}</h1>
<p>{answer}</p>
<h2>What is {topic}?</h2>
<p>{topic} helps teams improve visibility across search and AI assistants.</p>
<ul><li>Point one</li><li>Point two</li></ul>
<a href="/pricing">Pricing</a><a href="/about">About</a><a href="/contact">Contact</a>
</body></html>
"""

# (path, title, schema-type, topic)
_CLIENT_PAGES = [
    ("/", "Acme — AI-era SEO platform", "Organization", "answer engine optimization"),
    ("/pricing", "Acme Pricing & Plans", "Product", "pricing"),
    ("/solutions", "Acme Solutions for Enterprise", "Article", "enterprise SEO"),
    ("/guide", "The complete guide to AEO", "FAQPage", "AEO"),
    ("/about", "About Acme", "Organization", "the company"),
]


def _html(url: str, title: str, schema: str, topic: str) -> str:
    return _PAGE_HTML.format(
        url=url, title=title, schema=schema, topic=topic, h1=title,
        desc=f"{title} — concise, citable answers for SEO, AEO and GEO success.",
        answer=(
            f"{title} delivers a concise, direct answer of roughly forty to sixty words "
            f"so AI engines can quote it, covering {topic} with clear structure, schema "
            "and strong expertise signals for measurable organic growth."
        ),
    )


def _add_page(db, project_id, job_id, url, html, *, competitor=False, competitor_id=None,
              matched_page_id=None, rank=1.0):
    ex = extract(html, url, http_status=200)
    path = save_raw_html(project_id, job_id, url, html)
    page = Page(
        project_id=project_id, crawl_job_id=job_id, url=url, is_competitor=competitor,
        competitor_id=competitor_id, matched_page_id=matched_page_id, selected=True,
        rank_score=rank, fetch_method="seed", http_status=200, fetch_ok=True,
        raw_html_path=path, content_hash=content_hash(ex.cleaned_text),
        cleaned_text=ex.cleaned_text, title=ex.title, meta_description=ex.meta_description,
        word_count=ex.word_count, signals_json=__import__("json").dumps(ex.signals, default=str),
    )
    db.add(page)
    db.flush()
    return page


def seed(db) -> dict:
    seed_default_benchmarks(db)

    tenant = db.query(Tenant).filter(Tenant.slug == DEMO_TENANT_SLUG).one_or_none()
    if tenant is None:
        tenant = Tenant(name="Demo Co", slug=DEMO_TENANT_SLUG)
        db.add(tenant)
        db.flush()

    if not db.query(User).filter(User.email == DEMO_EMAIL).first():
        db.add(User(
            tenant_id=tenant.id, email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD), role=ROLE_ADMIN,
        ))

    project = (
        db.query(Project)
        .filter(Project.tenant_id == tenant.id, Project.name == "Acme Demo")
        .one_or_none()
    )
    if project is None:
        project = Project(
            tenant_id=tenant.id, name="Acme Demo", target_url="https://acme.com",
            industry="SEO software",
            competitors=[
                Competitor(name="Rival", url="https://rival.com"),
                Competitor(name="Foobar", url="https://foobar.com"),
            ],
        )
        db.add(project)
        db.flush()

    has_crawl = (
        db.query(CrawlJob)
        .filter(CrawlJob.project_id == project.id, CrawlJob.status == STATUS_DONE)
        .first()
    )
    if not has_crawl:
        job = CrawlJob(project_id=project.id, source_type=SOURCE_PASTE, status=STATUS_DONE)
        db.add(job)
        db.flush()
        competitors = list(project.competitors)
        total = 0
        for i, (path, title, schema, topic) in enumerate(_CLIENT_PAGES):
            url = "https://acme.com" + (path if path != "/" else "/")
            client_page = _add_page(
                db, project.id, job.id, url, _html(url, title, schema, topic),
                rank=1.0 - i * 0.1,
            )
            total += 1
            # One matched competitor page per competitor (weaker: no schema/answer).
            for comp in competitors:
                curl = comp.url.rstrip("/") + (path if path != "/" else "/")
                weak = f"<html><body><h2>{title}</h2><p>Buy now.</p></body></html>"
                _add_page(db, project.id, job.id, curl, weak, competitor=True,
                          competitor_id=comp.id, matched_page_id=client_page.id)
                total += 1
        job.total = job.processed = total

    db.commit()
    return {
        "tenant": tenant.slug, "email": DEMO_EMAIL, "password": DEMO_PASSWORD,
        "project_id": project.id,
    }


def main() -> None:
    from app.db.init_db import init_db

    init_db()
    db = SessionLocal()
    try:
        info = seed(db)
    finally:
        db.close()
    print("Seed complete:")
    print(f"  tenant   : {info['tenant']}")
    print(f"  login    : {info['email']} / {info['password']}")
    print(f"  project  : #{info['project_id']} (Acme Demo) with a completed crawl")
    print("Run a module analysis or the Leadership Dashboard to see results immediately.")


if __name__ == "__main__":
    main()
