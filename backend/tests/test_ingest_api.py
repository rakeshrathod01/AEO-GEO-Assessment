import io

import pytest
from openpyxl import Workbook

from tests.conftest import FakeFetcher


@pytest.fixture(autouse=True)
def _fake_default_fetcher(monkeypatch):
    """Inline ingestion builds the default fetcher; swap it for the fake one."""
    monkeypatch.setattr(
        "app.services.ingest.pipeline.build_default_fetcher",
        lambda *_args, **_kw: FakeFetcher(),
    )


def _make_project(client):
    r = client.post(
        "/api/v1/projects",
        json={
            "name": "Acme",
            "target_url": "https://acme.com",
            "competitors": [{"name": "Rival", "url": "https://rival.com"}],
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_paste_ingest_runs_inline_and_completes(client):
    pid = _make_project(client)
    r = client.post(
        f"/api/v1/projects/{pid}/ingest/paste",
        json={"text": "https://acme.com/\nhttps://acme.com/pricing", "top_n": 50},
    )
    assert r.status_code == 201
    job = r.json()
    assert job["status"] == "done"
    # 2 client + 2 mirrored competitor pages (competitor auto-derived from project).
    assert job["total"] == 4
    assert job["percent"] == 100

    pages = client.get(f"/api/v1/crawl/jobs/{job['id']}/pages").json()
    assert len(pages) == 4
    client_pages = [p for p in pages if not p["is_competitor"]]
    assert all(p["fetch_ok"] for p in client_pages)
    assert any(p["title"] for p in client_pages)


def test_paste_ingest_rejects_empty(client):
    pid = _make_project(client)
    r = client.post(f"/api/v1/projects/{pid}/ingest/paste", json={"text": "not a url ###"})
    assert r.status_code == 422


def test_excel_ingest(client):
    pid = _make_project(client)
    wb = Workbook()
    ws = wb.active
    ws.append(["URL"])
    ws.append(["https://acme.com/"])
    ws.append(["https://acme.com/solutions"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = client.post(
        f"/api/v1/projects/{pid}/ingest/excel",
        files={"file": ("urls.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"top_n": "50"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "done"
    assert r.json()["source_type"] == "excel"


def test_job_snapshot_and_listing(client):
    pid = _make_project(client)
    job = client.post(
        f"/api/v1/projects/{pid}/ingest/paste", json={"text": "https://acme.com/"}
    ).json()
    snap = client.get(f"/api/v1/crawl/jobs/{job['id']}")
    assert snap.status_code == 200
    assert snap.json()["id"] == job["id"]

    jobs = client.get(f"/api/v1/projects/{pid}/jobs").json()
    assert len(jobs) == 1


def test_ingest_unknown_project_404(client):
    r = client.post("/api/v1/projects/999/ingest/paste", json={"text": "https://x.com/"})
    assert r.status_code == 404
