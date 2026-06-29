from app.services.ingest.ranking import rank_urls, select_top


def test_homepage_ranks_first():
    urls = [
        "https://acme.com/blog/2021/05/some-post",
        "https://acme.com/",
        "https://acme.com/about/team/leadership",
    ]
    ranked = rank_urls(urls)
    assert ranked[0].url == "https://acme.com/"
    assert ranked[0].is_homepage


def test_money_pages_beat_deep_blog():
    urls = [
        "https://acme.com/pricing",
        "https://acme.com/blog/2021/05/12/a-long-tail-post-title",
    ]
    ranked = {r.url: r for r in rank_urls(urls)}
    assert ranked["https://acme.com/pricing"].is_money_page
    assert ranked["https://acme.com/pricing"].score > ranked[
        "https://acme.com/blog/2021/05/12/a-long-tail-post-title"
    ].score


def test_assets_and_low_value_penalized():
    urls = [
        "https://acme.com/solutions",
        "https://acme.com/files/whitepaper.pdf",
        "https://acme.com/tag/misc",
        "https://acme.com/privacy",
    ]
    ranked = rank_urls(urls)
    # The real page should outrank the asset and the legal/tag pages.
    assert ranked[0].url == "https://acme.com/solutions"
    assert ranked[-1].url in (
        "https://acme.com/files/whitepaper.pdf",
        "https://acme.com/tag/misc",
        "https://acme.com/privacy",
    )


def test_prominence_boosts_hub_pages():
    urls = [
        "https://acme.com/products",
        "https://acme.com/products/a",
        "https://acme.com/products/b",
        "https://acme.com/products/c",
        "https://acme.com/random-leaf",
    ]
    ranked = {r.url: r for r in rank_urls(urls)}
    assert "prominence" in ranked["https://acme.com/products"].reasons


def test_select_top_caps_and_is_deterministic():
    urls = [f"https://acme.com/p{i}" for i in range(120)]
    top = select_top(urls, n=50)
    assert len(top) == 50
    assert select_top(urls, n=50) == top  # deterministic


def test_sitemap_priority_influences_score():
    urls = ["https://acme.com/x", "https://acme.com/y"]
    ranked = {r.url: r for r in rank_urls(urls, priority_by_url={"https://acme.com/x": 1.0})}
    assert ranked["https://acme.com/x"].score > ranked["https://acme.com/y"].score
