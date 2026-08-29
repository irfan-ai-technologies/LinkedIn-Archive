"""Bundled sample data provider.

Ships fictional posts so that ``linkedin-archive sync`` (with
``sync.provider: sample`` in ``config.yaml``) and the whole downstream
pipeline — categorization, Markdown generation, static site build, search —
can be exercised end to end with zero external credentials. This is also
what CI and the test suite use.
"""

from __future__ import annotations

import json
from datetime import datetime
from importlib import resources

from app.ingestion.json_import import ImportFile
from app.ingestion.normalize import extract_links, guess_language
from app.models.media import Media
from app.models.post import RawPost

PROVIDER_NAME = "sample"


class SampleProvider:
    """Returns a fixed set of fictional posts bundled with the package."""

    name = PROVIDER_NAME

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        payload = json.loads(
            resources.files("app.ingestion")
            .joinpath("sample_data.json")
            .read_text(encoding="utf-8")
        )
        parsed = ImportFile.model_validate(payload)
        posts = [self._to_raw_post(item) for item in parsed.posts]
        if since is not None:
            posts = [p for p in posts if p.published_at >= since]
        return posts

    def _to_raw_post(self, item: object) -> RawPost:
        from app.ingestion.json_import import ImportPost

        assert isinstance(item, ImportPost)
        links = extract_links(item.text)
        media = [
            Media(type=m.type, url=m.url, title=m.title, alt_text=m.alt_text)  # type: ignore[arg-type]
            for m in item.media
        ]
        return RawPost(
            id=f"sample-{item.id}",
            source=PROVIDER_NAME,
            source_id=item.id,
            source_url=item.url,
            author=item.author or "Sample Author",
            published_at=item.published_at,
            updated_at=item.updated_at,
            text=item.text,
            title=item.title,
            media=media,
            links=links,
            hashtags=item.hashtags,
            language=item.language or guess_language(item.text),
            raw_metadata=item.model_dump(mode="json"),
        )
