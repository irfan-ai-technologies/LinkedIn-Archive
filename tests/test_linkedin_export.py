from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.ingestion.base import ProviderError
from app.ingestion.linkedin_export import LinkedInExportProvider
from app.models.media import MediaType


@pytest.fixture
def export_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "linkedin_export"


def test_fetch_posts_skips_bare_reposts_and_bad_dates(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir, default_author="Jane Doe")
    posts = provider.fetch_posts()
    # 6 rows in Shares.csv: one bare repost and one unparseable date are dropped.
    assert len(posts) == 4
    assert all(p.author == "Jane Doe" for p in posts)
    assert all(p.source == "linkedin_export" for p in posts)


def test_activity_id_extracted_from_share_link(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    posts = provider.fetch_posts()
    first = next(p for p in posts if "Excited to share" in p.text)
    assert first.id == "linkedin_export-7150000000000000001"
    assert first.source_id == "7150000000000000001"


def test_hashtags_extracted_from_text(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    posts = provider.fetch_posts()
    first = next(p for p in posts if "Excited to share" in p.text)
    assert "AgenticAI" in first.hashtags


def test_shared_url_becomes_a_link(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    posts = provider.fetch_posts()
    post = next(p for p in posts if "leadership" in p.text)
    assert any(link.url == "https://example.com/leadership-article" for link in post.links)


def test_media_url_with_image_extension_becomes_image_media(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    posts = provider.fetch_posts()
    post = next(p for p in posts if "sprint demo" in p.text)
    assert len(post.media) == 1
    assert post.media[0].type == MediaType.IMAGE
    assert post.media[0].url == "https://media.example.com/photo.jpg"


def test_missing_link_falls_back_to_deterministic_hash_id(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    posts_a = provider.fetch_posts()
    posts_b = provider.fetch_posts()
    post_a = next(p for p in posts_a if "No link on this one" in p.text)
    post_b = next(p for p in posts_b if "No link on this one" in p.text)
    assert post_a.id == post_b.id
    assert post_a.source_url is None


def test_since_filters_by_date(export_dir: Path) -> None:
    provider = LinkedInExportProvider(export_dir)
    all_posts = provider.fetch_posts()
    filtered = provider.fetch_posts(since=datetime(2026, 3, 1, tzinfo=UTC))
    expected = {
        p.source_id for p in all_posts if p.published_at >= datetime(2026, 3, 1, tzinfo=UTC)
    }
    assert {p.source_id for p in filtered} == expected
    assert expected == {
        "7150000000000000003",
        next(p.source_id for p in all_posts if "No link" in p.text),
    }


def test_missing_export_dir_raises_provider_error(tmp_path: Path) -> None:
    provider = LinkedInExportProvider(tmp_path / "does-not-exist")
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_shares_csv_without_recognizable_columns_raises_provider_error(tmp_path: Path) -> None:
    (tmp_path / "Shares.csv").write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    provider = LinkedInExportProvider(tmp_path)
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_only_bare_reposts_raises_provider_error(tmp_path: Path) -> None:
    (tmp_path / "Shares.csv").write_text(
        "Date,ShareLink,ShareCommentary,SharedUrl,MediaUrl\n"
        "2026-01-01 00:00:00,https://www.linkedin.com/posts/x-activity-7100000000000000009-Ab,,,\n",
        encoding="utf-8",
    )
    provider = LinkedInExportProvider(tmp_path)
    with pytest.raises(ProviderError):
        provider.fetch_posts()


def test_finds_member_id_suffixed_shares_file(tmp_path: Path) -> None:
    # LinkedIn's "Complete" export (as opposed to the "Posts"-only export)
    # suffixes this file with the member's numeric id, e.g. Shares_155814142.csv.
    (tmp_path / "Shares_155814142.csv").write_text(
        "Date,ShareLink,ShareCommentary,SharedUrl,MediaUrl\n"
        "2026-01-01 00:00:00,https://www.linkedin.com/posts/x-activity-7100000000000000009-Ab,"
        "Hello world,,\n",
        encoding="utf-8",
    )
    provider = LinkedInExportProvider(tmp_path)
    posts = provider.fetch_posts()
    assert len(posts) == 1


@pytest.mark.parametrize(
    ("link", "expected_id"),
    [
        (
            "https://www.linkedin.com/feed/update/urn%3Ali%3Ashare%3A7497901238773055488",
            "7497901238773055488",
        ),
        (
            "https://www.linkedin.com/feed/update/urn%3Ali%3AugcPost%3A7484213811479076864",
            "7484213811479076864",
        ),
        (
            "https://www.linkedin.com/feed/update/urn%3Ali%3AgroupPost%3A5096075-7152589185084706816",
            "7152589185084706816",
        ),
        (
            "https://www.linkedin.com/posts/janedoe_agenticai-activity-7150000000000000001-AbCd",
            "7150000000000000001",
        ),
    ],
)
def test_activity_id_extracted_from_real_linkedin_url_formats(
    tmp_path: Path, link: str, expected_id: str
) -> None:
    (tmp_path / "Shares.csv").write_text(
        f"Date,ShareLink,ShareCommentary,SharedUrl,MediaUrl\n2026-01-01 00:00:00,{link},Hello,,\n",
        encoding="utf-8",
    )
    provider = LinkedInExportProvider(tmp_path)
    posts = provider.fetch_posts()
    assert posts[0].source_id == expected_id
