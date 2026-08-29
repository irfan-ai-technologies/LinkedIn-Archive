"""Turns a :class:`RawPost` into a fully enriched :class:`Post`.

This is the single choke point between ingestion and storage: every
provider's output passes through here, so categorization, tagging, word
count, reading time, and excerpt generation behave identically regardless
of where the post came from.
"""

from __future__ import annotations

from app.enrichment.categorizer import Categorizer
from app.enrichment.metadata import (
    compute_reading_time_minutes,
    compute_word_count,
    derive_title,
    generate_excerpt,
)
from app.models.post import Post, RawPost


def enrich_post(
    raw: RawPost, categorizer: Categorizer, *, featured_ids: frozenset[str] = frozenset()
) -> Post:
    result = categorizer.categorize(raw)
    word_count = compute_word_count(raw.text)

    return Post(
        id=raw.id,
        source=raw.source,
        source_id=raw.source_id,
        source_url=raw.source_url,
        author=raw.author,
        published_at=raw.published_at,
        updated_at=raw.updated_at,
        title=derive_title(raw.text, raw.title),
        content=raw.text,
        excerpt=generate_excerpt(raw.text),
        media=raw.media,
        links=raw.links,
        hashtags=raw.hashtags,
        mentions=raw.mentions,
        category=result.category,
        tags=result.tags,
        featured=raw.id in featured_ids,
        language=raw.language,
        word_count=word_count,
        reading_time_minutes=compute_reading_time_minutes(word_count),
        raw_metadata=raw.raw_metadata,
    )
