import pytest

from tests.conftest import FakeAhrefs, FakeFetcher


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    monkeypatch.setattr(
        "app.services.ingest.pipeline.build_default_fetcher", lambda *_a, **_k: FakeFetcher()
    )
    monkeypatch.setattr(
        "app.services.analysis.runner.build_ahrefs_client", lambda _db: FakeAhrefs()
    )


def _project_with_crawl(client) -> int:
    pid = client.post(
        "/api/v1/projects",
        json={
            "name": "Acme",
            "target_url": "https://acme.com",
            "competitors": [{"name": "Rival", "url": "https://rival.com"}],
        },
    ).json()["id"]
    job = client.post(
        f"/api/v1/projects/{pid}/ingest/paste",
        json={"text": "https://acme.com/\nhttps://acme.com/pricing", "top_n": 50},
    ).json()
    assert job["status"] == "done"
    return pid


@pytest.mark.parametrize("module", ["internal_linking", "backlinks", "keyword_universe"])
def test_modules_return_contract(client, module):
    pid = _project_with_crawl(client)
    r = client.post(f"/api/v1/projects/{pid}/modules/{module}/analyze?scope=site")
    assert r.status_code == 200
    body = r.json()
    for key in ["scope", "target_url", "score", "status", "findings", "recommendations", "competitor_delta"]:
        assert key in body


def test_keyword_module_populates_serp_queries(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/keyword_universe/analyze?scope=site")
    rows = client.get(f"/api/v1/projects/{pid}/serp-queries").json()
    assert len(rows) > 0
    assert any(r["query_type"] == "paa" for r in rows)
    assert any(r["is_question"] for r in rows)

    paa_only = client.get(f"/api/v1/projects/{pid}/serp-queries?query_type=paa").json()
    assert all(r["query_type"] == "paa" for r in paa_only)


def test_backlinks_export_pdf(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/backlinks/analyze?scope=site")
    pdf = client.get(f"/api/v1/projects/{pid}/modules/backlinks/report.pdf?scope=site")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
