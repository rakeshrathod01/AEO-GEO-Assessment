import pytest

from tests.conftest import FakeFetcher


@pytest.fixture(autouse=True)
def _fake_default_fetcher(monkeypatch):
    monkeypatch.setattr(
        "app.services.ingest.pipeline.build_default_fetcher",
        lambda *_a, **_k: FakeFetcher(),
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


def test_analyze_site_returns_contract(client):
    pid = _project_with_crawl(client)
    r = client.post(f"/api/v1/projects/{pid}/modules/technical_seo/analyze?scope=site")
    assert r.status_code == 200
    body = r.json()
    for key in ["scope", "target_url", "score", "status", "findings", "recommendations", "competitor_delta"]:
        assert key in body
    assert 0 <= body["score"] <= 100
    assert body["competitor_delta"]  # Rival was crawled + compared


def test_analyze_page_scope(client):
    pid = _project_with_crawl(client)
    r = client.post(f"/api/v1/projects/{pid}/modules/on_page/analyze?scope=page")
    assert r.status_code == 200
    assert r.json()["scope"] == "page"


def test_analyze_without_crawl_409(client):
    pid = client.post(
        "/api/v1/projects", json={"name": "Empty", "target_url": "https://empty.com"}
    ).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/modules/technical_seo/analyze")
    assert r.status_code == 409


def test_export_excel_and_pdf(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/on_page/analyze?scope=site")

    xlsx = client.get(f"/api/v1/projects/{pid}/modules/on_page/export.xlsx?scope=site")
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"  # xlsx is a zip
    assert "attachment" in xlsx.headers["content-disposition"]

    pdf = client.get(f"/api/v1/projects/{pid}/modules/on_page/report.pdf?scope=site")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_export_before_analyze_409(client):
    pid = _project_with_crawl(client)
    r = client.get(f"/api/v1/projects/{pid}/modules/technical_seo/export.xlsx?scope=page")
    assert r.status_code == 409
