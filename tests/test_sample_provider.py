from datetime import UTC, datetime

from app.ingestion.sample import SampleProvider


def test_sample_provider_returns_posts() -> None:
    provider = SampleProvider()
    posts = provider.fetch_posts()
    assert len(posts) > 0
    assert all(p.source == "sample" for p in posts)
    assert all(p.id.startswith("sample-") for p in posts)


def test_sample_provider_is_deterministic() -> None:
    provider = SampleProvider()
    first = provider.fetch_posts()
    second = provider.fetch_posts()
    assert [p.id for p in first] == [p.id for p in second]


def test_sample_provider_since_filters() -> None:
    provider = SampleProvider()
    all_posts = provider.fetch_posts()
    cutoff = sorted(p.published_at for p in all_posts)[len(all_posts) // 2]
    filtered = provider.fetch_posts(since=cutoff)
    assert all(p.published_at >= cutoff for p in filtered)
    assert len(filtered) < len(all_posts)


def test_sample_provider_since_far_future_returns_nothing() -> None:
    provider = SampleProvider()
    assert provider.fetch_posts(since=datetime(2999, 1, 1, tzinfo=UTC)) == []
