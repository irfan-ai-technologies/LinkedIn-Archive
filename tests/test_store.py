from datetime import UTC, datetime
from pathlib import Path

from app.models.post import Post
from app.storage.store import PostStore


def _post(post_id: str, source: str = "sample") -> Post:
    return Post(
        id=post_id,
        source=source,
        source_id=post_id,
        author="Author",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        content="Some content",
        excerpt="Some content",
    )


def test_save_and_get_round_trip(tmp_path: Path) -> None:
    store = PostStore(tmp_path / "posts")
    store.save(_post("p1"))
    loaded = store.get("p1")
    assert loaded is not None
    assert loaded.id == "p1"


def test_get_missing_returns_none(tmp_path: Path) -> None:
    store = PostStore(tmp_path / "posts")
    assert store.get("nope") is None


def test_load_all_sorted_newest_first(tmp_path: Path) -> None:
    store = PostStore(tmp_path / "posts")
    older = _post("old").model_copy(update={"published_at": datetime(2020, 1, 1, tzinfo=UTC)})
    newer = _post("new").model_copy(update={"published_at": datetime(2026, 1, 1, tzinfo=UTC)})
    store.save(older)
    store.save(newer)
    posts = store.load_all()
    assert [p.id for p in posts] == ["new", "old"]


def test_delete_removes_file(tmp_path: Path) -> None:
    store = PostStore(tmp_path / "posts")
    store.save(_post("p1"))
    assert store.exists("p1")
    store.delete("p1")
    assert not store.exists("p1")


def test_all_ids_for_source_filters_by_source(tmp_path: Path) -> None:
    store = PostStore(tmp_path / "posts")
    store.save(_post("a", source="linkedin"))
    store.save(_post("b", source="import"))
    assert store.all_ids_for_source("linkedin") == {"a"}


def test_load_all_skips_malformed_files(tmp_path: Path) -> None:
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    (posts_dir / "broken.md").write_text("not front matter at all", encoding="utf-8")
    store = PostStore(posts_dir)
    store.save(_post("good"))
    posts = store.load_all()
    assert [p.id for p in posts] == ["good"]
