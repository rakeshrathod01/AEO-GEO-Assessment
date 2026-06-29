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
        json={"name": "Acme", "target_url": "https://acme.com",
              "competitors": [{"name": "Rival", "url": "https://rival.com"}]},
    ).json()["id"]
    client.post(
        f"/api/v1/projects/{pid}/ingest/paste",
        json={"text": "https://acme.com/\nhttps://acme.com/pricing", "top_n": 50},
    )
    return pid


def test_aeo_audit_contract_site_and_page(client):
    pid = _project_with_crawl(client)
    for scope in ("site", "page"):
        r = client.post(f"/api/v1/projects/{pid}/modules/aeo_audit/analyze?scope={scope}")
        assert r.status_code == 200
        body = r.json()
        assert body["scope"] == scope
        for key in ["score", "status", "findings", "recommendations", "competitor_delta"]:
            assert key in body
        assert any(f["signal"] == "ai_overview_readiness" for f in body["findings"])


def test_aeo_audit_export_pdf_and_excel(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/aeo_audit/analyze?scope=site")
    pdf = client.get(f"/api/v1/projects/{pid}/modules/aeo_audit/report.pdf?scope=site")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    xlsx = client.get(f"/api/v1/projects/{pid}/modules/aeo_audit/export.xlsx?scope=site")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
