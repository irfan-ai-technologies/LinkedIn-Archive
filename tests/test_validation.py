from app.config import AppConfig
from app.validation import validate_repository


def _write_post(config: AppConfig, filename: str, content: str) -> None:
    (config.posts_dir / filename).write_text(content, encoding="utf-8")


VALID_POST = """---
id: sample-1
source: sample
source_id: "1"
author: Author
published_at: 2026-01-01T00:00:00+00:00
category: General
---

Some body text.
"""


def test_no_issues_for_clean_repository(test_config: AppConfig) -> None:
    _write_post(test_config, "sample-1.md", VALID_POST)
    report = validate_repository(test_config)
    assert report.ok
    assert report.errors == []


def test_missing_posts_dir_is_a_warning_not_error(test_config: AppConfig) -> None:
    import shutil

    shutil.rmtree(test_config.posts_dir)
    report = validate_repository(test_config)
    assert report.ok
    assert report.warnings


def test_malformed_front_matter_is_an_error(test_config: AppConfig) -> None:
    _write_post(test_config, "broken.md", "---\nid: [unterminated\n---\n\nBody\n")
    report = validate_repository(test_config)
    assert not report.ok
    assert any("broken.md" in e for e in report.errors)


def test_duplicate_post_ids_are_an_error(test_config: AppConfig) -> None:
    _write_post(test_config, "a.md", VALID_POST)
    _write_post(test_config, "b.md", VALID_POST)
    report = validate_repository(test_config)
    assert not report.ok
    assert any("duplicate post id" in e for e in report.errors)


def test_unknown_category_is_a_warning(test_config: AppConfig) -> None:
    post = VALID_POST.replace("category: General", "category: Nonexistent Category")
    _write_post(test_config, "sample-1.md", post)
    report = validate_repository(test_config)
    assert report.ok
    assert any("Nonexistent Category" in w for w in report.warnings)


def test_future_published_at_is_a_warning(test_config: AppConfig) -> None:
    post = VALID_POST.replace("2026-01-01T00:00:00+00:00", "2999-01-01T00:00:00+00:00")
    _write_post(test_config, "sample-1.md", post)
    report = validate_repository(test_config)
    assert report.ok
    assert any("future" in w for w in report.warnings)


def test_broken_internal_link_is_an_error(test_config: AppConfig) -> None:
    post = VALID_POST + "\nSee also /posts/does-not-exist/ for more.\n"
    _write_post(test_config, "sample-1.md", post)
    report = validate_repository(test_config)
    assert not report.ok
    assert any("broken internal link" in e for e in report.errors)


def test_valid_internal_link_is_not_flagged(test_config: AppConfig) -> None:
    _write_post(test_config, "sample-1.md", VALID_POST)
    other = VALID_POST.replace("sample-1", "sample-2") + "\nSee /posts/sample-1/ for context.\n"
    _write_post(test_config, "sample-2.md", other)
    report = validate_repository(test_config)
    assert report.ok
