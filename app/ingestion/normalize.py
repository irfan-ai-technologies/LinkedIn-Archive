"""Shared text-normalization helpers used by every ingestion provider.

Keeping these here (rather than duplicated per-provider) guarantees that a
hashtag or link extracted from a LinkedIn payload and one extracted from a
hand-written JSON import behave identically once they reach enrichment.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.models.media import ExternalLink

_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_]*)")
_URL_RE = re.compile(r"https?://[^\s<>\)\]]+")
_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9][A-Za-z0-9._-]*(?: [A-Z][a-zA-Z-]*)*)")


def extract_hashtags(text: str) -> list[str]:
    """Extract unique hashtags (without the ``#``) in first-seen order."""
    seen: dict[str, None] = {}
    for match in _HASHTAG_RE.finditer(text):
        tag = match.group(1)
        seen.setdefault(tag, None)
    return list(seen.keys())


def extract_links(text: str) -> list[ExternalLink]:
    """Extract unique external links referenced in free text."""
    seen: dict[str, ExternalLink] = {}
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;:!?")
        if url in seen:
            continue
        domain = urlparse(url).netloc or None
        seen[url] = ExternalLink(url=url, domain=domain)
    return list(seen.values())


def strip_hashtags_and_urls_for_excerpt(text: str) -> str:
    """Collapse a post body into plain prose suitable for excerpt generation."""
    without_urls = _URL_RE.sub("", text)
    return re.sub(r"\s+", " ", without_urls).strip()


def guess_language(text: str) -> str | None:
    """Best-effort language hint. Returns ``"en"`` when the text is mostly
    ASCII letters, otherwise ``None`` (unknown) rather than guessing wrong.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    ascii_letters = sum(1 for c in letters if ord(c) < 128)
    return "en" if ascii_letters / len(letters) > 0.9 else None
