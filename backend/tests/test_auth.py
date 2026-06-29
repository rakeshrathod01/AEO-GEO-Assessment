import pytest

from app.core.config import settings


def _register(client, email, tenant_name="Acme"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret", "tenant_name": tenant_name},
    )


def test_register_login_me():
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = _register(client, "a@x.com")
        assert r.status_code == 201
        token = r.json()["access_token"]

        # duplicate email rejected
        assert _register(client, "a@x.com").status_code == 409

        login = client.post("/api/v1/auth/login", json={"email": "a@x.com", "password": "supersecret"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Bearer": token})  # wrong header
        assert me.status_code == 401
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200 and me.json()["email"] == "a@x.com"


def test_login_bad_password():
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        _register(client, "b@x.com")
        r = client.post("/api/v1/auth/login", json={"email": "b@x.com", "password": "wrong"})
        assert r.status_code == 401


def test_auth_required_enforced(monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    with TestClient(app) as client:
        # No token -> 401 on a protected route.
        assert client.get("/api/v1/projects").status_code == 401

        token = _register(client, "c@x.com").json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/projects", headers=h).status_code == 200


def test_tenant_isolation(monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    with TestClient(app) as client:
        t1 = _register(client, "t1@x.com", "Tenant One").json()["access_token"]
        t2 = _register(client, "t2@x.com", "Tenant Two").json()["access_token"]
        h1 = {"Authorization": f"Bearer {t1}"}
        h2 = {"Authorization": f"Bearer {t2}"}

        p1 = client.post("/api/v1/projects", json={"name": "P1", "target_url": "https://p1.com"},
                         headers=h1).json()
        client.post("/api/v1/projects", json={"name": "P2", "target_url": "https://p2.com"},
                    headers=h2)

        # Each tenant sees only its own project.
        list1 = client.get("/api/v1/projects", headers=h1).json()
        list2 = client.get("/api/v1/projects", headers=h2).json()
        assert [p["name"] for p in list1] == ["P1"]
        assert [p["name"] for p in list2] == ["P2"]

        # Tenant 2 cannot read tenant 1's project (404, not 403, to avoid leaking existence).
        assert client.get(f"/api/v1/projects/{p1['id']}", headers=h2).status_code == 404
        assert client.get(f"/api/v1/projects/{p1['id']}", headers=h1).status_code == 200


def test_api_keys_isolated_per_tenant(monkeypatch):
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    with TestClient(app) as client:
        t1 = _register(client, "k1@x.com", "K1").json()["access_token"]
        t2 = _register(client, "k2@x.com", "K2").json()["access_token"]
        h1 = {"Authorization": f"Bearer {t1}"}
        h2 = {"Authorization": f"Bearer {t2}"}

        client.put("/api/v1/settings/keys", json={"provider": "anthropic", "value": "sk-t1"},
                   headers=h1)
        # Tenant 2 has no keys; tenant 1 has one.
        assert len(client.get("/api/v1/settings/keys", headers=h1).json()) == 1
        assert client.get("/api/v1/settings/keys", headers=h2).json() == []
