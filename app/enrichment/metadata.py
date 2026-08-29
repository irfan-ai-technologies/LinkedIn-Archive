"""Derived metadata: word count, reading time, and excerpts."""

from __future__ import annotations

import re

from app.ingestion.normalize import strip_hashtags_and_urls_for_excerpt

_WORDS_PER_MINUTE = 200
_WORD_RE = re.compile(r"\S+")


def compute_word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def compute_reading_time_minutes(word_count: int, words_per_minute: int = _WORDS_PER_MINUTE) -> int:
    if word_count <= 0:
        return 1
    return max(1, round(word_count / words_per_minute))


def generate_excerpt(text: str, max_length: int = 220) -> str:
    """A short, plain-text summary suitable for cards, meta descriptions, and RSS."""
    clean = strip_hashtags_and_urls_for_excerpt(text)
    if len(clean) <= max_length:
        return clean
    truncated = clean[:max_length].rsplit(" ", 1)[0]
    return f"{truncated}…"


def derive_title(text: str, explicit_title: str | None, max_length: int = 80) -> str | None:
    """Fall back to the first line/sentence of the post when no title was supplied."""
    if explicit_title:
        return explicit_title
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    first_sentence = re.split(r"(?<=[.!?])\s", first_line, maxsplit=1)[0]
    candidate = first_sentence.strip()
    if not candidate:
        return None
    if len(candidate) > max_length:
        candidate = candidate[:max_length].rsplit(" ", 1)[0] + "…"
    return candidate
