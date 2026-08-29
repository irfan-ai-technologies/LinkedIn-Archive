"""Builds the compact client-side full-text search index.

The generated ``search-index.json`` is fetched once by the visitor's
browser and searched entirely client-side (see ``static/js/search.js``) —
no server, no database, no visitor query ever leaves the browser.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.models.post import Post
from app.site.urls import post_url


@dataclass(frozen=True)
class SearchIndexEntry:
    id: str
    title: str
    url: str
    excerpt: str
    content: str
    category: str
    tags: list[str]
    year: int
    author: str
    date: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "excerpt": self.excerpt,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "year": self.year,
            "author": self.author,
            "date": self.date,
        }


def build_search_index(
    posts: list[Post], *, max_indexed_chars: int = 4000
) -> list[dict[str, object]]:
    entries = [
        SearchIndexEntry(
            id=post.id,
            title=post.title or post.excerpt[:60],
            url=post_url(post.id),
            excerpt=post.excerpt,
            content=post.content[:max_indexed_chars],
            category=post.category,
            tags=sorted(post.tags),
            year=post.year,
            author=post.author,
            date=post.published_at.date().isoformat(),
        )
        for post in posts
    ]
    return [entry.to_dict() for entry in entries]


def dump_search_index(posts: list[Post], *, max_indexed_chars: int = 4000) -> str:
    """Deterministic, compact JSON suitable for committing to git."""
    data = {
        "generated_from": "linkedin-archive",
        "count": len(posts),
        "posts": build_search_index(posts, max_indexed_chars=max_indexed_chars),
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
