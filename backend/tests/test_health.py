from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "sqlite"


def test_ready(client: TestClient):
    r = client.get("/api/v1/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["api"] == "/api/v1"
