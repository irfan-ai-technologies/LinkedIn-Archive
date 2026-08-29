from datetime import UTC, datetime

from app.config import CategoryConfig
from app.enrichment.categorizer import KeywordCategorizer, _slugify_tag
from app.models.post import RawPost

CATEGORIES = [
    CategoryConfig(name="Agentic AI", slug="agentic-ai", priority=5, keywords=["agentic", "mcp"]),
    CategoryConfig(
        name="Software Engineering",
        slug="software-engineering",
        priority=20,
        keywords=["architecture", "engineering"],
    ),
    CategoryConfig(name="General", slug="general", priority=1000, keywords=[]),
]


def _raw(text: str, hashtags: list[str] | None = None) -> RawPost:
    return RawPost(
        id="p1",
        source="test",
        source_id="1",
        author="Someone",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        text=text,
        hashtags=hashtags or [],
    )


def test_primary_category_uses_priority_order() -> None:
    categorizer = KeywordCategorizer(CATEGORIES)
    # Matches both "agentic" (priority 5) and "engineering" (priority 20).
    result = categorizer.categorize(_raw("Agentic engineering is fun"))
    assert result.category == "Agentic AI"


def test_falls_back_to_general_when_nothing_matches() -> None:
    categorizer = KeywordCategorizer(CATEGORIES)
    result = categorizer.categorize(_raw("Just saying hello to everyone today"))
    assert result.category == "General"


def test_hashtag_match_is_case_insensitive() -> None:
    categorizer = KeywordCategorizer(CATEGORIES)
    result = categorizer.categorize(_raw("No keyword here", hashtags=["MCP"]))
    assert result.category == "Agentic AI"


def test_tags_include_hashtags_and_matched_category_slugs() -> None:
    categorizer = KeywordCategorizer(CATEGORIES)
    result = categorizer.categorize(_raw("architecture matters", hashtags=["SoftwareEngineering"]))
    assert "software-engineering" in result.tags
    # Deduplicated even though both the hashtag and the keyword match the
    # same category.
    assert result.tags.count("software-engineering") == 1


def test_slugify_tag_splits_camelcase_without_breaking_acronyms() -> None:
    assert _slugify_tag("AgenticAI") == "agentic-ai"
    assert _slugify_tag("AIEngineering") == "ai-engineering"
    assert _slugify_tag("MCP") == "mcp"
    assert _slugify_tag("SoftwareArchitecture") == "software-architecture"
