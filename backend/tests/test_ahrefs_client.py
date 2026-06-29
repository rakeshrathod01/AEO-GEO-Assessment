from datetime import date

from app.db.session import SessionLocal
from app.models.setting import ApiKey
from app.services.ahrefs.client import AhrefsClient, trailing_window


def test_trailing_window_is_six_months():
    f, t = trailing_window(months=6, today=date(2026, 6, 29))
    assert t == "2026-06-29"
    assert f == "2025-12-28"  # day clamped to 28


def test_trailing_window_wraps_year():
    f, _ = trailing_window(months=6, today=date(2026, 2, 15))
    assert f.startswith("2025-08")


def test_disabled_without_mcp_url():
    db = SessionLocal()
    try:
        client = AhrefsClient.from_db(db)
        assert client.enabled is False
        assert client.backlinks_stats("https://acme.com") is None
        assert client.organic_keywords("https://acme.com") == []
    finally:
        db.close()


def test_cached_tool_uses_transport_once(monkeypatch):
    db = SessionLocal()
    try:
        db.add(ApiKey.from_plaintext("ahrefs_mcp_url", "https://mcp.example.com"))
        db.commit()
        client = AhrefsClient.from_db(db)
        assert client.enabled

        calls = {"n": 0}

        def fake_call(tool, args):
            calls["n"] += 1
            return {"domain_rating": 61, "referring_domains": 200}

        monkeypatch.setattr(client, "_call_tool", fake_call)
        first = client.backlinks_stats("https://acme.com")
        second = client.backlinks_stats("https://acme.com")  # served from cache
        assert first == second
        assert first["domain_rating"] == 61
        assert calls["n"] == 1  # transport hit only once
    finally:
        db.close()
