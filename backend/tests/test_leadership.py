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


def test_leadership_synthesis_contract(client):
    pid = _project_with_crawl(client)
    r = client.post(f"/api/v1/projects/{pid}/leadership?scope=site")
    assert r.status_code == 200
    rep = r.json()

    # All eight modules scored.
    assert len(rep["modules"]) == 8
    assert set(rep["layer_scores"].keys()) == {"SEO", "AEO", "GEO"}
    assert 0 <= rep["overall_score"] <= 100
    assert rep["synthesis_source"] == "deterministic"  # no Opus key in tests

    # Roadmap is ordered foundational SEO -> AEO -> GEO.
    phases = [i["phase"] for i in rep["roadmap"]]
    assert phases == sorted(phases, key=["SEO", "AEO", "GEO"].index)
    assert all(i["order"] for i in rep["roadmap"])

    # Benchmarks carry sources (for hover tooltips).
    assert rep["benchmarks"] and all(b["source"] for b in rep["benchmarks"])


def test_leadership_page_rescope(client):
    pid = _project_with_crawl(client)
    pages = client.get(f"/api/v1/projects/{pid}/pages").json()
    assert pages
    page_id = pages[0]["id"]
    r = client.post(f"/api/v1/projects/{pid}/leadership?scope=page&page_id={page_id}")
    assert r.status_code == 200
    assert r.json()["scope"] == "page"
    assert r.json()["target_url"] == pages[0]["url"]


def test_master_excel_and_leadership_pdf(client):
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/leadership?scope=site")

    xlsx = client.get(f"/api/v1/projects/{pid}/leadership/export.xlsx?scope=site")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"

    pdf = client.get(f"/api/v1/projects/{pid}/leadership/report.pdf?scope=site")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_export_before_synthesis_409(client):
    pid = _project_with_crawl(client)
    r = client.get(f"/api/v1/projects/{pid}/leadership/export.xlsx?scope=site")
    assert r.status_code == 409


def test_pitch_deck_download(client, monkeypatch):
    # Keep the deck offline + deterministic (no logo fetch).
    monkeypatch.setattr("app.services.exports.deck._default_fetch_logo", lambda _d: None)
    pid = _project_with_crawl(client)
    client.post(f"/api/v1/projects/{pid}/leadership?scope=site")
    pptx = client.get(f"/api/v1/projects/{pid}/leadership/deck.pptx?scope=site")
    assert pptx.status_code == 200
    assert pptx.content[:2] == b"PK"
    assert "presentationml" in pptx.headers["content-type"]


def test_pitch_deck_before_synthesis_409(client):
    pid = _project_with_crawl(client)
    r = client.get(f"/api/v1/projects/{pid}/leadership/deck.pptx?scope=site")
    assert r.status_code == 409


def test_pages_empty_without_crawl(client):
    pid = client.post(
        "/api/v1/projects", json={"name": "Empty", "target_url": "https://e.com"}
    ).json()["id"]
    assert client.get(f"/api/v1/projects/{pid}/pages").json() == []
