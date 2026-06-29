import pytest

from tests.conftest import FakeAhrefs, FakeFetcher, fake_geo_providers


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    monkeypatch.setattr(
        "app.services.ingest.pipeline.build_default_fetcher", lambda *_a, **_k: FakeFetcher()
    )
    monkeypatch.setattr(
        "app.services.analysis.runner.build_ahrefs_client", lambda _db, _t=None: FakeAhrefs()
    )
    monkeypatch.setattr(
        "app.services.analysis.runner.build_providers", lambda _db, _t=None: fake_geo_providers()
    )


def _project_with_crawl(client) -> int:
    pid = client.post(
        "/api/v1/projects",
        json={"name": "Acme", "target_url": "https://acme.com", "industry": "SEO",
              "competitors": [{"name": "Rival", "url": "https://rival.com"}]},
    ).json()["id"]
    client.post(
        f"/api/v1/projects/{pid}/ingest/paste",
        json={"text": "https://acme.com/\nhttps://acme.com/pricing", "top_n": 50},
    )
    return pid


def test_prompt_identification_populates_prompts(client):
    pid = _project_with_crawl(client)
    # Keyword Universe feeds prompt generation with SERP seed queries (real pipeline).
    client.post(f"/api/v1/projects/{pid}/modules/keyword_universe/analyze?scope=site")
    r = client.post(f"/api/v1/projects/{pid}/modules/prompt_identification/analyze?scope=site")
    assert r.status_code == 200
    prompts = client.get(f"/api/v1/projects/{pid}/prompts").json()
    assert 45 <= len(prompts) <= 65
    assert {p["intent_bucket"] for p in prompts} >= {"comparison", "transactional"}


def test_prompts_export(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/prompt_identification/analyze?scope=site")
    xlsx = client.get(f"/api/v1/projects/{pid}/prompts/export.xlsx")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    pdf = client.get(f"/api/v1/projects/{pid}/prompts/export.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_geo_audit_contract_and_results(client):
    pid = _project_with_crawl(client)
    r = client.post(f"/api/v1/projects/{pid}/modules/geo_audit/analyze?scope=site")
    assert r.status_code == 200
    body = r.json()
    assert any(f["signal"] == "geo_visibility" for f in body["findings"])
    assert body["competitor_delta"]

    results = client.get(f"/api/v1/projects/{pid}/geo-results").json()
    assert len(results) > 0
    assert {r["source_kind"] for r in results} == {"api", "serp"}
    # Filter by provider.
    serp = client.get(f"/api/v1/projects/{pid}/geo-results?provider=ai_overview").json()
    assert all(r["source_kind"] == "serp" for r in serp)


def test_geo_audit_export_pdf(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/modules/geo_audit/analyze?scope=site")
    pdf = client.get(f"/api/v1/projects/{pid}/modules/geo_audit/report.pdf?scope=site")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
