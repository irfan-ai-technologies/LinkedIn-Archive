"""Deterministic Markdown + YAML front matter serialization for posts.

Given the same :class:`Post`, :func:`post_to_markdown` always produces
byte-identical output — no timestamps, no nondeterministic ordering — so
that re-running sync without content changes produces an empty git diff.
"""

from __future__ import annotations

import frontmatter
import yaml
from pydantic import ValidationError

from app.models.post import Post

# Fields serialized into front matter, in this fixed order, for readable diffs.
_FIELD_ORDER = [
    "id",
    "source",
    "source_id",
    "source_url",
    "author",
    "published_at",
    "updated_at",
    "title",
    "category",
    "tags",
    "hashtags",
    "featured",
    "language",
    "word_count",
    "reading_time_minutes",
    "excerpt",
    "media",
    "links",
    "mentions",
]


class FrontMatterError(ValueError):
    """Raised when a Markdown file cannot be parsed into a Post."""


def _ordered_dump(data: dict[str, object]) -> str:
    class _OrderedDumper(yaml.SafeDumper):
        pass

    def _represent_dict(dumper: yaml.SafeDumper, value: dict[str, object]) -> yaml.MappingNode:
        items = [(key, value[key]) for key in _FIELD_ORDER if key in value]
        items += [(k, v) for k, v in value.items() if k not in _FIELD_ORDER]
        return dumper.represent_mapping("tag:yaml.org,2002:map", items)

    _OrderedDumper.add_representer(dict, _represent_dict)
    return yaml.dump(
        data,
        Dumper=_OrderedDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def post_to_markdown(post: Post) -> str:
    data: dict[str, object] = {
        "id": post.id,
        "source": post.source,
        "source_id": post.source_id,
        "source_url": post.source_url,
        "author": post.author,
        "published_at": post.published_at.isoformat(),
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "title": post.title,
        "category": post.category,
        "tags": post.tags,
        "hashtags": post.hashtags,
        "featured": post.featured,
        "language": post.language,
        "word_count": post.word_count,
        "reading_time_minutes": post.reading_time_minutes,
        "excerpt": post.excerpt,
        "media": [m.model_dump(mode="json") for m in post.media],
        "links": [link.model_dump(mode="json") for link in post.links],
        "mentions": [m.model_dump(mode="json") for m in post.mentions],
    }
    data = {k: v for k, v in data.items() if v is not None}
    front = _ordered_dump(data)
    body = post.content.strip()
    return f"---\n{front}---\n\n{body}\n"


def markdown_to_post(text: str, *, raw_metadata: dict[str, object] | None = None) -> Post:
    try:
        parsed = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"invalid YAML front matter: {exc}") from exc

    data = dict(parsed.metadata)
    required = {"id", "source", "source_id", "author", "published_at"}
    missing = required - data.keys()
    if missing:
        raise FrontMatterError(f"missing required front matter fields: {sorted(missing)}")

    payload: dict[str, object] = {
        "id": data.get("id"),
        "source": data.get("source"),
        "source_id": str(data.get("source_id")),
        "source_url": data.get("source_url"),
        "author": data.get("author"),
        "published_at": data.get("published_at"),
        "updated_at": data.get("updated_at"),
        "title": data.get("title"),
        "content": parsed.content,
        "excerpt": data.get("excerpt", ""),
        "media": data.get("media", []),
        "links": data.get("links", []),
        "hashtags": data.get("hashtags", []),
        "mentions": data.get("mentions", []),
        "category": data.get("category", "General"),
        "tags": data.get("tags", []),
        "featured": data.get("featured", False),
        "language": data.get("language"),
        "word_count": data.get("word_count", 0),
        "reading_time_minutes": data.get("reading_time_minutes", 1),
        "raw_metadata": raw_metadata or {},
    }
    try:
        return Post.model_validate(payload)
    except ValidationError as exc:
        raise FrontMatterError(f"invalid post data: {exc}") from exc
