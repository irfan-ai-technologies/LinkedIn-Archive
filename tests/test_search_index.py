import json
from datetime import UTC, datetime

from app.models.post import Post
from app.search.index import build_search_index, dump_search_index


def _post(post_id: str, content: str = "hello world") -> Post:
    return Post(
        id=post_id,
        source="sample",
        source_id=post_id,
        author="Author",
        published_at=datetime(2026, 3, 15, tzinfo=UTC),
        title="Title " + post_id,
        content=content,
        excerpt=content[:50],
        category="Agentic AI",
        tags=["agentic-ai", "mcp"],
    )


def test_build_search_index_shape() -> None:
    entries = build_search_index([_post("1")])
    assert entries[0]["id"] == "1"
    assert entries[0]["url"] == "/posts/1/"
    assert entries[0]["category"] == "Agentic AI"
    assert entries[0]["tags"] == ["agentic-ai", "mcp"]
    assert entries[0]["year"] == 2026


def test_content_truncated_to_max_chars() -> None:
    entries = build_search_index([_post("1", content="x" * 1000)], max_indexed_chars=100)
    assert len(entries[0]["content"]) == 100  # type: ignore[arg-type]


def test_dump_search_index_is_valid_json() -> None:
    dumped = dump_search_index([_post("1"), _post("2")])
    data = json.loads(dumped)
    assert data["count"] == 2
    assert len(data["posts"]) == 2


def test_dump_search_index_is_deterministic() -> None:
    posts = [_post("1"), _post("2")]
    assert dump_search_index(posts) == dump_search_index(posts)
