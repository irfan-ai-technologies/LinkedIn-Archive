from datetime import UTC, datetime

from app.config import AppConfig
from app.ingestion.base import ProviderError
from app.models.post import RawPost
from app.storage.store import PostStore
from app.sync import run_sync


class _StaticProvider:
    name = "test"

    def __init__(self, posts: list[RawPost]) -> None:
        self._posts = posts

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        return list(self._posts)


class _FailingProvider:
    name = "test"

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        raise ProviderError(self.name, "boom")


def _raw(post_id: str, text: str = "Some agentic engineering text") -> RawPost:
    return RawPost(
        id=f"test-{post_id}",
        source="test",
        source_id=post_id,
        author="Author",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        text=text,
    )


def test_first_sync_creates_new_posts(test_config: AppConfig) -> None:
    result = run_sync(_StaticProvider([_raw("1"), _raw("2")]), test_config)
    assert result.fetched == 2
    assert result.new == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert PostStore(test_config.posts_dir).load_all()


def test_second_identical_sync_is_idempotent(test_config: AppConfig) -> None:
    provider = _StaticProvider([_raw("1"), _raw("2")])
    run_sync(provider, test_config)
    result = run_sync(provider, test_config)
    assert result.new == 0
    assert result.updated == 0
    assert result.unchanged == 2
    # No duplicate files were created.
    assert len(PostStore(test_config.posts_dir).load_all()) == 2


def test_changed_content_is_detected_as_updated(test_config: AppConfig) -> None:
    run_sync(_StaticProvider([_raw("1", "original text")]), test_config)
    result = run_sync(_StaticProvider([_raw("1", "edited text")]), test_config)
    assert result.updated == 1
    assert result.new == 0
    post = PostStore(test_config.posts_dir).get("test-1")
    assert post is not None
    assert "edited" in post.content


def test_featured_flag_is_preserved_across_updates(test_config: AppConfig) -> None:
    store = PostStore(test_config.posts_dir)
    run_sync(_StaticProvider([_raw("1", "original text")]), test_config)
    post = store.get("test-1")
    assert post is not None
    post.featured = True
    store.save(post)

    run_sync(_StaticProvider([_raw("1", "edited text")]), test_config)
    updated = store.get("test-1")
    assert updated is not None
    assert updated.featured is True
    assert "edited" in updated.content


def test_preserve_deleted_keeps_missing_posts_by_default(test_config: AppConfig) -> None:
    run_sync(_StaticProvider([_raw("1"), _raw("2")]), test_config)
    run_sync(_StaticProvider([_raw("1")]), test_config)
    assert PostStore(test_config.posts_dir).get("test-2") is not None


def test_preserve_deleted_false_removes_vanished_posts(test_config: AppConfig) -> None:
    test_config.user.sync.preserve_deleted = False
    run_sync(_StaticProvider([_raw("1"), _raw("2")]), test_config)
    run_sync(_StaticProvider([_raw("1")]), test_config)
    assert PostStore(test_config.posts_dir).get("test-2") is None
    assert PostStore(test_config.posts_dir).get("test-1") is not None


def test_sync_never_deletes_other_sources(test_config: AppConfig) -> None:
    test_config.user.sync.preserve_deleted = False
    run_sync(_StaticProvider([_raw("1")]), test_config)

    class _OtherProvider(_StaticProvider):
        name = "other"

    run_sync(_OtherProvider([]), test_config)
    assert PostStore(test_config.posts_dir).get("test-1") is not None


def test_provider_failure_is_reported_without_raising(test_config: AppConfig) -> None:
    result = run_sync(_FailingProvider(), test_config)
    assert result.failed == 1
    assert result.fetched == 0
    assert "boom" in result.errors[0]


def test_categories_counted_for_touched_posts(test_config: AppConfig) -> None:
    result = run_sync(
        _StaticProvider([_raw("1", "agentic systems"), _raw("2", "software architecture")]),
        test_config,
    )
    assert result.categories["Agentic AI"] == 1
    assert result.categories["Software Engineering"] == 1
