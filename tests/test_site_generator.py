from datetime import UTC, datetime

from app.config import AppConfig
from app.enrichment.categorizer import KeywordCategorizer
from app.enrichment.pipeline import enrich_post
from app.models.post import RawPost
from app.site.generator import build_site
from app.storage.store import PostStore


def _seed_posts(config: AppConfig, count: int) -> None:
    categorizer = KeywordCategorizer(config.user.sorted_categories())
    store = PostStore(config.posts_dir)
    for i in range(count):
        raw = RawPost(
            id=f"sample-{i}",
            source="sample",
            source_id=str(i),
            source_url=f"https://www.linkedin.com/posts/x-{i}",
            author="Test Author",
            published_at=datetime(2026, (i % 12) + 1, 1, tzinfo=UTC),
            text=f"Post number {i} about agentic engineering and architecture. #AgenticAI",
        )
        post = enrich_post(raw, categorizer)
        if i == 0:
            post.featured = True
        store.save(post)


def test_build_produces_expected_top_level_pages(test_config: AppConfig) -> None:
    _seed_posts(test_config, 5)
    dist = build_site(test_config)

    for relative in [
        "index.html",
        "about/index.html",
        "posts/index.html",
        "categories/index.html",
        "tags/index.html",
        "archive/index.html",
        "search/index.html",
        "feed.xml",
        "sitemap.xml",
        "robots.txt",
        "search-index.json",
        "404.html",
        "static/css/style.css",
        "static/js/search.js",
    ]:
        assert (dist / relative).exists(), f"missing {relative}"


def test_build_generates_a_page_per_post(test_config: AppConfig) -> None:
    _seed_posts(test_config, 3)
    dist = build_site(test_config)
    for i in range(3):
        assert (dist / "posts" / f"sample-{i}" / "index.html").exists()


def test_pagination_creates_additional_pages(test_config: AppConfig) -> None:
    # test_config sets posts_per_page = 4
    _seed_posts(test_config, 10)
    dist = build_site(test_config)
    assert (dist / "posts" / "index.html").exists()
    assert (dist / "posts" / "page" / "2" / "index.html").exists()
    assert (dist / "posts" / "page" / "3" / "index.html").exists()
    assert not (dist / "posts" / "page" / "4").exists()


def test_category_and_tag_pages_generated(test_config: AppConfig) -> None:
    _seed_posts(test_config, 5)
    dist = build_site(test_config)
    assert (dist / "categories" / "agentic-ai" / "index.html").exists()
    assert (dist / "tags" / "agentic-ai" / "index.html").exists()


def test_search_index_contains_all_posts(test_config: AppConfig) -> None:
    import json

    _seed_posts(test_config, 4)
    dist = build_site(test_config)
    data = json.loads((dist / "search-index.json").read_text(encoding="utf-8"))
    assert data["count"] == 4


def test_internal_links_between_posts_resolve(test_config: AppConfig) -> None:
    _seed_posts(test_config, 3)
    dist = build_site(test_config)
    html = (dist / "posts" / "sample-0" / "index.html").read_text(encoding="utf-8")
    # Featured post 0 should link to its neighbor.
    assert "/posts/sample-1/" in html


def test_build_is_deterministic(test_config: AppConfig) -> None:
    _seed_posts(test_config, 4)
    build_site(test_config)
    first = (test_config.dist_dir / "index.html").read_text(encoding="utf-8")
    build_site(test_config)
    second = (test_config.dist_dir / "index.html").read_text(encoding="utf-8")
    assert first == second


def test_build_with_no_posts_still_produces_site(test_config: AppConfig) -> None:
    dist = build_site(test_config)
    assert (dist / "index.html").exists()
    assert (dist / "search-index.json").exists()


def test_rss_and_sitemap_reference_configured_site_url(test_config: AppConfig) -> None:
    _seed_posts(test_config, 2)
    dist = build_site(test_config)
    rss = (dist / "feed.xml").read_text(encoding="utf-8")
    sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert test_config.site_url in rss
    assert test_config.site_url in sitemap


def test_post_page_has_no_script_tags_from_content(test_config: AppConfig) -> None:
    categorizer = KeywordCategorizer(test_config.user.sorted_categories())
    store = PostStore(test_config.posts_dir)
    raw = RawPost(
        id="xss-post",
        source="sample",
        source_id="xss",
        author="Author",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        text="Hello <script>alert(1)</script> world",
    )
    store.save(enrich_post(raw, categorizer))
    dist = build_site(test_config)
    html = (dist / "posts" / "xss-post" / "index.html").read_text(encoding="utf-8")
    assert "<script>alert" not in html
