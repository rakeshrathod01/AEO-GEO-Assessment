from app.services.ingest.sitemap import fetch_sitemap_entries, parse_sitemap_xml
from app.services.ingest.urls import dedupe_normalized, normalize_url, parse_pasted_urls

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://acme.com/</loc><priority>1.0</priority></url>
  <url><loc>https://acme.com/pricing</loc><priority>0.8</priority></url>
  <url><loc>https://acme.com/pricing#plans</loc></url>
</urlset>"""

INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://acme.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://acme.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>"""


def test_parse_urlset():
    parsed = parse_sitemap_xml(URLSET)
    urls = {e.url for e in parsed.entries}
    # The fragment URL normalizes to the same as /pricing -> deduped by dict in fetch,
    # but parse keeps both entries; normalization strips the fragment.
    assert "https://acme.com/" in urls
    assert "https://acme.com/pricing" in urls
    prio = {e.url: e.priority for e in parsed.entries}
    assert prio["https://acme.com/"] == 1.0


def test_parse_index():
    parsed = parse_sitemap_xml(INDEX)
    assert not parsed.entries
    assert parsed.child_sitemaps == [
        "https://acme.com/sitemap-1.xml",
        "https://acme.com/sitemap-2.xml",
    ]


def test_fetch_follows_index():
    pages = {
        "https://acme.com/sitemap.xml": INDEX,
        "https://acme.com/sitemap-1.xml": URLSET,
        "https://acme.com/sitemap-2.xml": (
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>https://acme.com/contact</loc></url></urlset>"
        ),
    }
    entries = fetch_sitemap_entries(
        "https://acme.com/sitemap.xml", fetch_text=lambda u: pages[u]
    )
    urls = {e.url for e in entries}
    assert "https://acme.com/contact" in urls
    assert "https://acme.com/pricing" in urls


def test_normalize_url():
    assert normalize_url("acme.com") == "https://acme.com/"
    assert normalize_url("https://Acme.com/Page/") == "https://acme.com/Page"
    assert normalize_url("https://acme.com/p#frag") == "https://acme.com/p"
    assert normalize_url("ftp://x") is None
    assert normalize_url("   ") is None


def test_paste_parsing_mixed_separators():
    text = "https://a.com/1, https://a.com/2\nhttps://a.com/1\n  b.com/3 "
    urls = parse_pasted_urls(text)
    assert urls == ["https://a.com/1", "https://a.com/2", "https://b.com/3"]


def test_dedupe_normalized():
    assert dedupe_normalized(["a.com", "https://a.com/", "a.com/x"]) == [
        "https://a.com/",
        "https://a.com/x",
    ]
