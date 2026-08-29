"""The synchronization engine: fetch → normalize → enrich → store, idempotently.

This module intentionally contains no provider-specific or template-specific
code — it only depends on :class:`~app.ingestion.base.ContentProvider`,
the enrichment pipeline, and :class:`~app.storage.store.PostStore`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from app.config import AppConfig
from app.enrichment.categorizer import KeywordCategorizer
from app.enrichment.pipeline import enrich_post
from app.ingestion.base import ContentProvider, ProviderError
from app.models.post import Post
from app.storage.raw_archive import RawArchive
from app.storage.store import PostStore

# Fields compared to decide whether a re-fetched post counts as "updated".
# `featured` is deliberately excluded: it is a manual, owner-controlled flag
# that sync must never overwrite based on source data.
_COMPARISON_FIELDS = (
    "title",
    "content",
    "excerpt",
    "category",
    "tags",
    "hashtags",
    "media",
    "links",
    "updated_at",
)


@dataclass
class SyncResult:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    categories: Counter[str] = field(default_factory=Counter)

    @property
    def touched(self) -> int:
        return self.new + self.updated

    def summary_text(self) -> str:
        lines = [
            "LinkedIn Archive Sync",
            "",
            f"Fetched:    {self.fetched:>6}",
            f"New:        {self.new:>6}",
            f"Updated:    {self.updated:>6}",
            f"Unchanged:  {self.unchanged:>6}",
            f"Failed:     {self.failed:>6}",
        ]
        if self.categories:
            lines += ["", "Categories:"]
            for name, count in sorted(self.categories.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"  {name:<24} {count}")
        if self.errors:
            lines += ["", "Errors:"]
            lines += [f"  - {err}" for err in self.errors]
        return "\n".join(lines)


def _has_changed(candidate: Post, existing: Post) -> bool:
    return any(getattr(candidate, f) != getattr(existing, f) for f in _COMPARISON_FIELDS)


def run_sync(
    provider: ContentProvider,
    config: AppConfig,
    *,
    since: datetime | None = None,
) -> SyncResult:
    """Fetch from ``provider`` and reconcile against the on-disk post store."""
    store = PostStore(config.posts_dir)
    raw_archive = RawArchive(config.raw_dir)
    categorizer = KeywordCategorizer(config.user.sorted_categories())

    result = SyncResult()

    try:
        raw_posts = provider.fetch_posts(since=since)
    except ProviderError as exc:
        result.failed += 1
        result.errors.append(str(exc))
        return result

    result.fetched = len(raw_posts)

    for raw in raw_posts:
        try:
            raw_archive.save(raw)
            candidate = enrich_post(raw, categorizer)
            existing = store.get(candidate.id)

            if existing is None:
                store.save(candidate)
                result.new += 1
                result.categories[candidate.category] += 1
            elif _has_changed(candidate, existing):
                candidate.featured = existing.featured
                store.save(candidate)
                result.updated += 1
                result.categories[candidate.category] += 1
            else:
                result.unchanged += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{raw.id}: {exc}")

    if not config.user.sync.preserve_deleted:
        _remove_vanished_posts(store, provider.name, {r.id for r in raw_posts})

    return result


def _remove_vanished_posts(store: PostStore, source: str, fetched_ids: set[str]) -> None:
    """Delete posts from ``source`` that no longer appear in the latest fetch.

    Only ever touches posts belonging to the source that was just synced, so
    an import or sample post is never deleted by a LinkedIn sync.
    """
    for post_id in store.all_ids_for_source(source) - fetched_ids:
        store.delete(post_id)
