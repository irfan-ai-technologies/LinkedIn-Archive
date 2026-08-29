from datetime import UTC, datetime

from app.models.post import Post
from app.stats import compute_stats


def _post(post_id: str, year: int, category: str, tags: list[str], words: int) -> Post:
    return Post(
        id=post_id,
        source="sample",
        source_id=post_id,
        author="Author",
        published_at=datetime(year, 1, 1, tzinfo=UTC),
        content="word " * words,
        excerpt="excerpt",
        category=category,
        tags=tags,
        word_count=words,
    )


def test_compute_stats_empty() -> None:
    stats = compute_stats([])
    assert stats.total_posts == 0
    assert stats.latest_post is None


def test_compute_stats_aggregates_correctly() -> None:
    posts = [
        _post("1", 2025, "AI", ["ai", "ml"], 100),
        _post("2", 2026, "AI", ["ai"], 200),
        _post("3", 2026, "Leadership", ["career"], 300),
    ]
    stats = compute_stats(posts)
    assert stats.total_posts == 3
    assert stats.by_year[2026] == 2
    assert stats.by_category["AI"] == 2
    assert stats.by_tag["ai"] == 2
    assert stats.average_word_count == 200
    assert stats.latest_post is not None
    assert stats.latest_post.id in {"2", "3"}
