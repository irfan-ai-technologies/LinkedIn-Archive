"""The content provider abstraction.

Every source of posts — LinkedIn's API, a local JSON import, bundled sample
data, or any future source (RSS, another social platform, manual Markdown)
— implements :class:`ContentProvider`. Nothing outside of ``app.ingestion``
may depend on a concrete provider; the sync engine, CLI, and tests all talk
to this interface only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.models.post import RawPost


@runtime_checkable
class ContentProvider(Protocol):
    """A source of raw posts."""

    name: str

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        """Return raw posts, optionally limited to those published since ``since``.

        Implementations should be defensive: a provider that cannot filter
        server-side may fetch everything and filter locally, but must never
        raise merely because ``since`` is unsupported.
        """
        ...


@dataclass(frozen=True)
class ProviderError(Exception):
    """Raised when a provider fails to fetch or parse content."""

    provider: str
    message: str

    def __str__(self) -> str:
        return f"[{self.provider}] {self.message}"
