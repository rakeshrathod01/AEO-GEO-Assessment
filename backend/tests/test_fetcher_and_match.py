from app.services.ingest.competitor_match import match_by_similarity, mirror_client_paths
from app.services.ingest.fetcher import CompositeFetcher, FetchResult, needs_fallback


class _Stub:
    def __init__(self, result: FetchResult):
        self.result = result
        self.called = False

    def fetch(self, url: str) -> FetchResult:
        self.called = True
        return self.result


def _ok(html="<html><body>" + ("content " * 100) + "</body></html>"):
    return FetchResult(url="u", method="firecrawl", success=True, status_code=200, html=html)


def test_needs_fallback_on_failure():
    assert needs_fallback(FetchResult(url="u", method="firecrawl", success=False))


def test_needs_fallback_on_block_status():
    assert needs_fallback(
        FetchResult(url="u", method="firecrawl", success=True, status_code=403, html="x" * 9999)
    )


def test_needs_fallback_on_challenge_marker():
    html = "<html><body>Just a moment... checking your browser</body></html>"
    assert needs_fallback(FetchResult(url="u", method="firecrawl", success=True, status_code=200, html=html))


def test_needs_fallback_on_thin_content():
    assert needs_fallback(FetchResult(url="u", method="firecrawl", success=True, status_code=200, html="<html></html>"))


def test_no_fallback_on_good_content():
    assert not needs_fallback(_ok())


def test_composite_uses_fallback_when_primary_thin():
    primary = _Stub(FetchResult(url="u", method="firecrawl", success=True, status_code=200, html="<html></html>"))
    fallback = _Stub(_ok())
    comp = CompositeFetcher(primary, fallback)
    result = comp.fetch("u")
    assert fallback.called
    assert result.method == "firecrawl"  # _ok() default method label
    assert result.success


def test_composite_skips_fallback_when_primary_good():
    primary = _Stub(_ok())
    fallback = _Stub(_ok())
    comp = CompositeFetcher(primary, fallback)
    comp.fetch("u")
    assert not fallback.called


def test_mirror_client_paths():
    client = ["https://acme.com/pricing", "https://acme.com/about"]
    matches = mirror_client_paths(client, "rival.com")
    urls = {m.competitor_url for m in matches}
    assert "https://rival.com/pricing" in urls
    assert "https://rival.com/about" in urls
    assert all(m.score == 1.0 for m in matches)


def test_match_by_similarity_prefers_exact_path():
    client = ["https://acme.com/pricing", "https://acme.com/contact-us"]
    comp = ["https://rival.com/pricing", "https://rival.com/contact", "https://rival.com/blog"]
    matches = {m.client_url: m.competitor_url for m in match_by_similarity(client, comp)}
    assert matches["https://acme.com/pricing"] == "https://rival.com/pricing"
    # contact-us best-matches /contact
    assert matches["https://acme.com/contact-us"] == "https://rival.com/contact"
