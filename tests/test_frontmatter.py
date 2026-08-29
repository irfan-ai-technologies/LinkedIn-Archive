from datetime import UTC, datetime

import pytest

from app.models.post import Post
from app.storage.frontmatter import FrontMatterError, markdown_to_post, post_to_markdown


def _post(**overrides: object) -> Post:
    defaults: dict[str, object] = {
        "id": "linkedin-123",
        "source": "linkedin",
        "source_id": "123",
        "source_url": "https://www.linkedin.com/posts/x-123",
        "author": "Jane Doe",
        "published_at": datetime(2026, 8, 20, 10, 30, tzinfo=UTC),
        "title": "A great post",
        "content": "Hello **world**, check #AgenticAI",
        "excerpt": "Hello world, check",
        "category": "Agentic AI",
        "tags": ["agentic-ai"],
        "hashtags": ["AgenticAI"],
        "featured": True,
        "language": "en",
        "word_count": 5,
        "reading_time_minutes": 1,
    }
    defaults.update(overrides)
    return Post(**defaults)  # type: ignore[arg-type]


def test_round_trip_preserves_fields() -> None:
    post = _post()
    markdown = post_to_markdown(post)
    restored = markdown_to_post(markdown)

    assert restored.id == post.id
    assert restored.source == post.source
    assert restored.source_id == post.source_id
    assert restored.author == post.author
    assert restored.published_at == post.published_at
    assert restored.title == post.title
    assert restored.category == post.category
    assert restored.tags == post.tags
    assert restored.hashtags == post.hashtags
    assert restored.featured == post.featured
    assert restored.content.strip() == post.content.strip()


def test_serialization_is_deterministic() -> None:
    post = _post()
    assert post_to_markdown(post) == post_to_markdown(post)


def test_front_matter_has_readable_field_order() -> None:
    markdown = post_to_markdown(_post())
    front = markdown.split("---")[1]
    assert front.index("id:") < front.index("source:") < front.index("published_at:")


def test_missing_required_fields_raises() -> None:
    with pytest.raises(FrontMatterError):
        markdown_to_post("---\ntitle: Missing stuff\n---\n\nBody text\n")


def test_malformed_yaml_raises() -> None:
    with pytest.raises(FrontMatterError):
        markdown_to_post("---\nid: [unterminated\n---\n\nBody\n")


def test_defaults_applied_for_optional_fields() -> None:
    minimal = (
        "---\n"
        "id: import-1\n"
        "source: import\n"
        "source_id: '1'\n"
        "author: Someone\n"
        "published_at: 2026-01-01T00:00:00+00:00\n"
        "---\n\n"
        "Body text here.\n"
    )
    post = markdown_to_post(minimal)
    assert post.category == "General"
    assert post.tags == []
    assert post.featured is False
    assert post.word_count == 0
    assert post.reading_time_minutes == 1
