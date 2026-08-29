"""Local JSON import provider.

This is the always-available provider: it requires no LinkedIn credentials
and no network access, which makes the rest of the application (site
generation, search, categorization) fully testable and usable even before a
fork owner has LinkedIn API access.

Documented import format
-------------------------
::

    {
      "posts": [
        {
          "id": "123",                                  // required, unique
          "published_at": "2026-08-20T10:30:00Z",         // required, ISO-8601
          "text": "...",                                  // required
          "url": "https://www.linkedin.com/...",           // optional
          "title": "...",                                  // optional
          "author": "Jane Doe",                            // optional
          "updated_at": "2026-08-21T09:00:00Z",            // optional
          "hashtags": ["AI", "AgenticAI"],                 // optional
          "media": [                                       // optional
            {"type": "image", "url": "https://...", "alt_text": "..."}
          ],
          "language": "en"                                 // optional
        }
      ]
    }

Any fields not recognized are preserved in ``raw_metadata`` for the record.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.ingestion.base import ProviderError
from app.ingestion.normalize import extract_hashtags, extract_links, guess_language
from app.models.media import Media
from app.models.post import RawPost

PROVIDER_NAME = "import"


class ImportMedia(BaseModel):
    type: str = "image"
    url: str
    title: str | None = None
    alt_text: str | None = None


class ImportPost(BaseModel):
    id: str
    published_at: datetime
    text: str
    url: str | None = None
    title: str | None = None
    author: str | None = None
    updated_at: datetime | None = None
    hashtags: list[str] = Field(default_factory=list)
    media: list[ImportMedia] = Field(default_factory=list)
    language: str | None = None


class ImportFile(BaseModel):
    posts: list[ImportPost] = Field(default_factory=list)


class JsonImportProvider:
    """Reads a documented JSON file into normalized :class:`RawPost` objects."""

    name = PROVIDER_NAME

    def __init__(self, path: Path | str, default_author: str = "Unknown") -> None:
        self.path = Path(path)
        self.default_author = default_author

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        if not self.path.exists():
            raise ProviderError(self.name, f"import file not found: {self.path}")

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            parsed = ImportFile.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ProviderError(self.name, f"invalid import file: {exc}") from exc

        posts = [self._to_raw_post(item) for item in parsed.posts]
        if since is not None:
            posts = [p for p in posts if p.published_at >= since]
        return posts

    def _to_raw_post(self, item: ImportPost) -> RawPost:
        hashtags = item.hashtags or extract_hashtags(item.text)
        links = extract_links(item.text)
        media = [
            Media(type=m.type, url=m.url, title=m.title, alt_text=m.alt_text)  # type: ignore[arg-type]
            for m in item.media
        ]
        return RawPost(
            id=f"import-{item.id}",
            source=PROVIDER_NAME,
            source_id=item.id,
            source_url=item.url,
            author=item.author or self.default_author,
            published_at=item.published_at,
            updated_at=item.updated_at,
            text=item.text,
            title=item.title,
            media=media,
            links=links,
            hashtags=hashtags,
            language=item.language or guess_language(item.text),
            raw_metadata=item.model_dump(mode="json"),
        )
