from fastapi.testclient import TestClient


def test_upsert_and_mask_api_key(client: TestClient):
    r = client.put(
        "/api/v1/settings/keys",
        json={"provider": "anthropic", "value": "sk-ant-abcdef123456", "label": "primary"},
    )
    assert r.status_code == 200
    body = r.json()
    # Plaintext never returned — only a masked preview.
    assert "sk-ant" not in body["masked_value"]
    assert body["masked_value"].endswith("3456")
    assert body["provider"] == "anthropic"


def test_upsert_replaces_existing(client: TestClient):
    client.put("/api/v1/settings/keys", json={"provider": "openai", "value": "key-one"})
    client.put("/api/v1/settings/keys", json={"provider": "openai", "value": "key-two-xyz"})
    r = client.get("/api/v1/settings/keys")
    keys = [k for k in r.json() if k["provider"] == "openai"]
    assert len(keys) == 1  # replaced, not duplicated


def test_unsupported_provider_rejected(client: TestClient):
    r = client.put("/api/v1/settings/keys", json={"provider": "evilcorp", "value": "x"})
    assert r.status_code == 422


def test_empty_value_rejected(client: TestClient):
    r = client.put("/api/v1/settings/keys", json={"provider": "anthropic", "value": "   "})
    assert r.status_code == 422


def test_providers_catalog(client: TestClient):
    r = client.get("/api/v1/settings/providers")
    assert r.status_code == 200
    catalog = r.json()
    keys = {p["key"] for p in catalog}
    assert {"ahrefs_mcp_url", "firecrawl", "anthropic", "openai", "gemini", "perplexity"} <= keys
    ahrefs = next(p for p in catalog if p["key"] == "ahrefs_mcp_url")
    assert ahrefs["kind"] == "url" and ahrefs["required"] is True
    assert ahrefs["configured"] is False


def test_url_kind_returned_in_full(client: TestClient):
    client.put(
        "/api/v1/settings/keys",
        json={"provider": "ahrefs_mcp_url", "value": "https://ahrefs-mcp.example.com"},
    )
    r = client.get("/api/v1/settings/keys")
    ahrefs = next(k for k in r.json() if k["provider"] == "ahrefs_mcp_url")
    assert ahrefs["kind"] == "url"
    assert ahrefs["value"] == "https://ahrefs-mcp.example.com"  # not masked

    # And a secret stays masked.
    client.put("/api/v1/settings/keys", json={"provider": "anthropic", "value": "sk-ant-secret123"})
    r2 = client.get("/api/v1/settings/keys")
    anth = next(k for k in r2.json() if k["provider"] == "anthropic")
    assert anth["value"] is None
    assert "sk-ant" not in anth["masked_value"]


def test_list_modules_returns_nine(client: TestClient):
    r = client.get("/api/v1/modules")
    assert r.status_code == 200
    modules = r.json()
    assert len(modules) == 9
    assert modules[0]["key"] == "technical_seo"
    assert modules[-1]["key"] == "leadership"


def test_module_analyze_returns_contract(client: TestClient):
    r = client.post(
        "/api/v1/modules/technical_seo/analyze",
        params={"target_url": "https://example.com", "scope": "page"},
    )
    assert r.status_code == 200
    body = r.json()
    assert set(["scope", "target_url", "score", "status", "findings", "recommendations",
                "competitor_delta"]).issubset(body.keys())


def test_project_crud(client: TestClient):
    r = client.post(
        "/api/v1/projects",
        json={
            "name": "Acme Audit",
            "target_url": "https://acme.com",
            "industry": "SaaS",
            "competitors": [{"name": "Rival", "url": "https://rival.com"}],
        },
    )
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["competitors"][0]["name"] == "Rival"

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200

    r3 = client.delete(f"/api/v1/projects/{pid}")
    assert r3.status_code == 204
    assert client.get(f"/api/v1/projects/{pid}").status_code == 404
