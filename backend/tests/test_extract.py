from app.services.ingest.extract import extract

SAMPLE = """
<html lang="en-US">
<head>
  <title>Acme Pricing</title>
  <meta name="description" content="Plans and pricing for Acme.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="Acme Pricing OG">
  <link rel="canonical" href="https://acme.com/pricing">
  <script type="application/ld+json">{"@type":"Product","name":"Acme"}</script>
  <style>.x{color:red}</style>
</head>
<body>
  <h1>Pricing</h1>
  <h2>Plans</h2><h2>FAQ</h2>
  <p>Choose the plan that fits your team and budget today.</p>
  <img src="a.png" alt="chart">
  <img src="b.png">
  <a href="/features">Features</a>
  <a href="https://twitter.com/acme">Twitter</a>
  <script>var tracking = 1;</script>
</body>
</html>
"""


def test_extract_onpage_signals():
    ex = extract(SAMPLE, "https://acme.com/pricing", http_status=200)
    s = ex.signals
    assert ex.title == "Acme Pricing"
    assert ex.meta_description == "Plans and pricing for Acme."
    assert s["h1"] == ["Pricing"]
    assert s["h2_count"] == 2
    assert s["images_count"] == 2
    assert s["images_missing_alt"] == 1
    assert s["internal_links"] == 1
    assert s["external_links"] == 1
    assert s["og_title"] == "Acme Pricing OG"
    assert ex.word_count > 0
    # Script/style text is stripped from cleaned text.
    assert "tracking" not in ex.cleaned_text
    assert "color:red" not in ex.cleaned_text


def test_extract_technical_signals():
    s = extract(SAMPLE, "https://acme.com/pricing", http_status=200).signals
    assert s["has_canonical"] is True
    assert s["canonical"] == "https://acme.com/pricing"
    assert s["has_viewport_meta"] is True
    assert s["lang"] == "en-US"
    assert s["is_noindex"] is False
    assert s["has_structured_data"] is True
    assert "Product" in s["structured_data_types"]
    assert s["http_status"] == 200
    assert 0 < s["text_to_html_ratio"] <= 1


def test_extract_noindex_detected():
    html = "<html><head><meta name='robots' content='noindex,nofollow'></head><body>x</body></html>"
    s = extract(html, "https://acme.com/x").signals
    assert s["is_noindex"] is True
