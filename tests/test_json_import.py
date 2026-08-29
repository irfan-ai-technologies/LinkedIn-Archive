from pathlib import Path

import pytest

from app.ingestion.base import ProviderError
from app.ingestion.json_import import JsonImportProvider


def test_import_parses_fixture_file(fixtures_dir: Path) -> None:
    provider = JsonImportProvider(fixtures_dir / "import_posts.json", default_author="Fallback")
    posts = provider.fetch_posts()
    assert len(posts) == 3
    assert posts[0].id == "import-1001"
    assert posts[0].source == "import"
    assert posts[0].source_id == "1001"
    assert "AgenticAI" in posts[0].hashtags or "AgenticAI" in "".join(posts[0].hashtags)


def test_import_extracts_hashtags_when_not_provided(fixtures_dir: Path) -> None:
    provider = JsonImportProvider(fixtures_dir / "import_posts.json", default_author="Fallback")
    posts = provider.fetch_posts()
    second = next(p for p in posts if p.source_id == "1002")
    assert "SoftwareEngineering" in second.hashtags


def test_import_falls_back_to_default_author(fixtures_dir: Path, tmp_path: Path) -> None:
    data = tmp_path / "posts.json"
    data.write_text(
        '{"posts": [{"id": "1", "published_at": "2026-01-01T00:00:00Z", "text": "hello"}]}',
        encoding="utf-8",
    )
    provider = JsonImportProvider(data, default_author="Fallback Author")
    posts = provider.fetch_posts()
    assert posts[0].author == "Fallback Author"


def test_import_missing_file_raises_provider_error(tmp_path: Path) -> None:
    provider = JsonImportProvider(tmp_path / "missing.json", default_author="X")
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_import_invalid_json_raises_provider_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    provider = JsonImportProvider(bad, default_author="X")
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_import_missing_required_field_raises_provider_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"posts": [{"id": "1"}]}', encoding="utf-8")
    provider = JsonImportProvider(bad, default_author="X")
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_import_since_filters_by_date(fixtures_dir: Path) -> None:
    from datetime import UTC, datetime

    provider = JsonImportProvider(fixtures_dir / "import_posts.json", default_author="X")
    posts = provider.fetch_posts(since=datetime(2026, 2, 10, tzinfo=UTC))
    assert {p.source_id for p in posts} == {"1002", "1003"}
