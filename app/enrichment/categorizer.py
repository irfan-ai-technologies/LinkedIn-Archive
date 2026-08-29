"""Post categorization.

The default :class:`KeywordCategorizer` is purely rule-based and configured
entirely from ``config.yaml`` — no fork owner needs to touch Python code to
change their categories. :class:`Categorizer` is a small interface so an
LLM-based (or otherwise pluggable) categorizer can be added later without
touching the rest of the enrichment pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.config import CategoryConfig
from app.models.post import RawPost

_DEFAULT_CATEGORY = "General"


@dataclass(frozen=True)
class CategoryResult:
    category: str
    tags: list[str]


class Categorizer(Protocol):
    def categorize(self, post: RawPost) -> CategoryResult: ...


_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _slugify_tag(value: str) -> str:
    """Slugify a hashtag, splitting CamelCase words without breaking acronyms.

    ``AgenticAI`` -> ``agentic-ai``, ``AIEngineering`` -> ``ai-engineering``,
    ``MCP`` -> ``mcp`` (an all-caps acronym is left intact).
    """
    value = _CAMEL_BOUNDARY_RE.sub("-", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value.lower()


class KeywordCategorizer:
    """Matches post text and hashtags against configured keyword lists.

    * The **primary category** is the highest-priority (lowest ``priority``
      number) configured category with at least one matching keyword or
      hashtag. If nothing matches, posts fall back to ``"General"``.
    * **Tags** are the union of: every hashtag on the post (slugified), plus
      the slug of every category (not just the primary one) whose keywords
      matched.
    """

    def __init__(self, categories: list[CategoryConfig]) -> None:
        self._categories = sorted(categories, key=lambda c: c.priority)

    def categorize(self, post: RawPost) -> CategoryResult:
        haystack = f" {post.text.lower()} "
        hashtag_set = {tag.lower() for tag in post.hashtags}

        primary: str | None = None
        matched_slugs: list[str] = []

        for category in self._categories:
            matched = any(
                keyword.lower() in haystack or keyword.lower().strip() in hashtag_set
                for keyword in category.keywords
            )
            if matched:
                matched_slugs.append(category.slug)
                if primary is None:
                    primary = category.name

        tags = list(dict.fromkeys([_slugify_tag(t) for t in post.hashtags] + matched_slugs))
        return CategoryResult(category=primary or _DEFAULT_CATEGORY, tags=tags)
