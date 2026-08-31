from pathlib import Path

import pytest

from app.ingestion.base import ProviderError
from app.ingestion.linkedin_profile_import import merge_profile, parse_profile_csv
from app.models.profile import Profile, ProfileLinks


@pytest.fixture
def export_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "linkedin_export"


def test_parse_profile_csv_extracts_expected_fields(export_dir: Path) -> None:
    parsed = parse_profile_csv(export_dir / "Profile.csv")
    assert parsed.name == "Jane Doe"
    assert parsed.headline is not None
    assert parsed.headline.startswith("Software architect")
    assert parsed.bio is not None
    assert "agentic systems in production" in parsed.bio
    assert parsed.location == "San Francisco Bay Area"


def test_parse_profile_csv_missing_file_raises_provider_error(tmp_path: Path) -> None:
    with pytest.raises(ProviderError):
        parse_profile_csv(tmp_path / "Profile.csv")


def test_parse_profile_csv_unrecognized_columns_raises_provider_error(tmp_path: Path) -> None:
    bad = tmp_path / "Profile.csv"
    bad.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ProviderError):
        parse_profile_csv(bad)


def test_merge_profile_overrides_name_headline_bio_location(export_dir: Path) -> None:
    existing = Profile(
        name="Placeholder Name",
        headline="Placeholder headline",
        bio="Placeholder bio",
        location="Placeholder location",
        avatar="avatar.png",
        links=ProfileLinks(
            linkedin="https://www.linkedin.com/in/janedoe", github="https://github.com/janedoe"
        ),
    )
    parsed = parse_profile_csv(export_dir / "Profile.csv")
    merged = merge_profile(existing, parsed)

    assert merged.name == "Jane Doe"
    assert merged.headline == parsed.headline
    assert merged.bio == parsed.bio
    assert merged.location == "San Francisco Bay Area"


def test_merge_profile_never_touches_avatar_or_links(export_dir: Path) -> None:
    existing = Profile(
        name="Placeholder",
        avatar="avatar.png",
        links=ProfileLinks(
            linkedin="https://www.linkedin.com/in/janedoe", github="https://github.com/janedoe"
        ),
    )
    parsed = parse_profile_csv(export_dir / "Profile.csv")
    merged = merge_profile(existing, parsed)

    assert merged.avatar == "avatar.png"
    assert merged.links == existing.links


def test_merge_profile_preserves_fields_absent_from_partial_export(export_dir: Path) -> None:
    existing = Profile(
        name="Placeholder", headline="Old headline", bio="Old bio", location="Old location"
    )
    parsed = parse_profile_csv(export_dir / "Profile_partial.csv")
    merged = merge_profile(existing, parsed)

    assert merged.headline == "Updated headline only"
    assert merged.bio == "Old bio"
    assert merged.location == "Old location"
