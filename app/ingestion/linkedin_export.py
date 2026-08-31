"""LinkedIn personal data-export provider (Posts).

Reads ``Shares.csv`` from LinkedIn's own "Download my data" export
(Settings & Privacy -> Data privacy -> Get a copy of your data -> select
the **Posts** checkbox) instead of calling the LinkedIn API. As of this
writing, LinkedIn is not accepting new access requests for the
``r_member_social`` scope the ``linkedin`` provider needs (its own
Marketing API FAQ calls the permission "closed... due to resource
constraints"), so this is the only way most forks can populate an archive
from their real post history today. See ``docs/linkedin-api.md``.

This is not scraping: LinkedIn generates this export and hands it directly
to the member who requested it. Nothing in this module talks to LinkedIn at
all — it only reads a file already sitting on disk.

Column names have varied across LinkedIn export format revisions, so every
column lookup is case/punctuation-insensitive and tries a short list of
known aliases (see ``app/ingestion/csv_utils.py``). If none match, a clear
:class:`~app.ingestion.base.ProviderError` reports the headers actually
found in the file so the aliases can be extended.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from dateutil import parser as date_parser

from app.ingestion.base import ProviderError
from app.ingestion.csv_utils import find_column
from app.ingestion.normalize import extract_hashtags, extract_links, guess_language
from app.models.media import ExternalLink, Media, MediaType
from app.models.post import RawPost

PROVIDER_NAME = "linkedin_export"

_SHARES_FILENAME = "Shares.csv"

_DATE_ALIASES = ("Date",)
_TEXT_ALIASES = ("ShareCommentary", "Share Commentary", "Commentary", "Text")
_LINK_ALIASES = ("ShareLink", "Share Link", "Link", "Url", "Post Url")
_SHARED_URL_ALIASES = ("SharedUrl", "Shared Url", "SharedURL")
_MEDIA_ALIASES = ("MediaUrl", "Media Url", "MediaURL")

_ACTIVITY_ID_RE = re.compile(r"activity[:-](\d{6,})")
_IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|gif|webp|bmp)(\?|$)", re.IGNORECASE)
_VIDEO_EXT_RE = re.compile(r"\.(mp4|mov|avi|webm)(\?|$)", re.IGNORECASE)


@dataclass(frozen=True)
class _Columns:
    date: str | None
    text: str | None
    link: str | None
    shared_url: str | None
    media: str | None


def _cell(row: dict[str, str], column: str | None) -> str:
    if column is None:
        return ""
    return (row.get(column) or "").strip()


class LinkedInExportProvider:
    """Reads ``Shares.csv`` from a LinkedIn "Download my data" export folder."""

    name = PROVIDER_NAME

    def __init__(self, export_dir: Path | str, default_author: str = "Unknown") -> None:
        self.export_dir = Path(export_dir)
        self.default_author = default_author

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        path = self._find_shares_file()
        rows = self._read_rows(path)
        columns = self._resolve_columns(rows[0].keys() if rows else [])

        posts = [post for row in rows if (post := self._row_to_post(row, columns)) is not None]

        if rows and not posts:
            raise ProviderError(
                self.name,
                f"{path} was read but no row produced a usable post (every row was missing "
                f"both text and a shared link) — headers found: {sorted(rows[0].keys())}",
            )

        if since is not None:
            posts = [p for p in posts if p.published_at >= since]
        return posts

    def _find_shares_file(self) -> Path:
        candidate = self.export_dir / _SHARES_FILENAME
        if candidate.exists():
            return candidate
        # Some export zips nest CSVs under a "Basic_LinkedInDataExport_*" folder.
        for match in sorted(self.export_dir.rglob(_SHARES_FILENAME)):
            return match
        raise ProviderError(
            self.name,
            f"{_SHARES_FILENAME} not found under {self.export_dir} — make sure you selected "
            "the 'Posts' checkbox when requesting your LinkedIn data export and extracted the zip",
        )

    def _read_rows(self, path: Path) -> list[dict[str, str]]:
        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                if reader.fieldnames is None:
                    raise ProviderError(self.name, f"{path} has no header row")
                return list(reader)
        except OSError as exc:
            raise ProviderError(self.name, f"could not read {path}: {exc}") from exc
        except csv.Error as exc:
            raise ProviderError(self.name, f"invalid CSV in {path}: {exc}") from exc

    def _resolve_columns(self, fieldnames: Iterable[str]) -> _Columns:
        fields = list(fieldnames)
        columns = _Columns(
            date=find_column(fields, *_DATE_ALIASES),
            text=find_column(fields, *_TEXT_ALIASES),
            link=find_column(fields, *_LINK_ALIASES),
            shared_url=find_column(fields, *_SHARED_URL_ALIASES),
            media=find_column(fields, *_MEDIA_ALIASES),
        )
        if columns.date is None or (columns.text is None and columns.link is None):
            raise ProviderError(
                self.name,
                f"{_SHARES_FILENAME} doesn't have a recognizable date/text column — "
                f"headers found: {sorted(fields)}",
            )
        return columns

    def _row_to_post(self, row: dict[str, str], columns: _Columns) -> RawPost | None:
        text = _cell(row, columns.text)
        link = _cell(row, columns.link) or None
        shared_url = _cell(row, columns.shared_url) or None
        media_url = _cell(row, columns.media) or None

        if not text and not shared_url:
            return None  # a bare repost with nothing archivable

        published_at = self._parse_date(_cell(row, columns.date))
        if published_at is None:
            return None

        source_id = self._derive_id(link, published_at, text)
        links = extract_links(text)
        if shared_url and not any(existing.url == shared_url for existing in links):
            links.append(ExternalLink(url=shared_url, domain=urlparse(shared_url).netloc or None))

        media = [Media(type=self._guess_media_type(media_url), url=media_url)] if media_url else []

        return RawPost(
            id=f"{PROVIDER_NAME}-{source_id}",
            source=PROVIDER_NAME,
            source_id=source_id,
            source_url=link,
            author=self.default_author,
            published_at=published_at,
            text=text,
            media=media,
            links=links,
            hashtags=extract_hashtags(text),
            language=guess_language(text),
            raw_metadata=dict(row),
        )

    @staticmethod
    def _parse_date(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            parsed = date_parser.parse(raw)
        except (ValueError, OverflowError, TypeError):
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @staticmethod
    def _derive_id(link: str | None, published_at: datetime, text: str) -> str:
        if link:
            match = _ACTIVITY_ID_RE.search(link)
            if match:
                return match.group(1)
        # No activity id could be recovered from the link (or there was no
        # link) — fall back to a deterministic hash of the row's content so
        # re-running the import always yields the same id, never a random one.
        digest = hashlib.sha1(f"{published_at.isoformat()}|{text}".encode()).hexdigest()
        return digest[:16]

    @staticmethod
    def _guess_media_type(url: str) -> MediaType:
        if _IMAGE_EXT_RE.search(url):
            return MediaType.IMAGE
        if _VIDEO_EXT_RE.search(url):
            return MediaType.VIDEO
        return MediaType.LINK
