"""The provider-independent Post model.

Every content provider (LinkedIn, JSON import, sample data, or any future
provider) normalizes its native data into a :class:`RawPost`, and the
enrichment pipeline turns that into a fully-populated :class:`Post`. Nothing
outside of ``app.ingestion`` is allowed to know about provider-specific
shapes (LinkedIn API fields, JSON import schema, etc.) — the rest of the
application only ever depends on these two models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.media import ExternalLink, Media, Mention


class RawPost(BaseModel):
    """A post as fetched from a provider, before enrichment.

    This is the contract every :class:`app.ingestion.base.ContentProvider`
    must produce. It carries enough information to normalize into a
    :class:`Post` without ever calling back to the source, but it has not
    yet been categorized, tagged, or had derived metadata (word count,
    reading time, excerpt) computed.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable identifier, unique within its source.")
    source: str = Field(description='Provider name, e.g. "linkedin", "import", "sample".')
    source_id: str = Field(description="The identifier as assigned by the source system.")
    source_url: str | None = Field(default=None, description="Permalink to the original post.")
    author: str
    published_at: datetime
    updated_at: datetime | None = None
    text: str = Field(description="Plain or lightly-marked-up post body.")
    title: str | None = None
    media: list[Media] = Field(default_factory=list)
    links: list[ExternalLink] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[Mention] = Field(default_factory=list)
    language: str | None = None
    raw_metadata: dict[str, object] = Field(
        default_factory=dict,
        description="The original provider payload, preserved for future reprocessing.",
    )


class Post(BaseModel):
    """A fully normalized, enriched post ready for storage and publishing."""

    model_config = ConfigDict(frozen=False)

    # --- Identity -----------------------------------------------------
    id: str
    source: str
    source_id: str
    source_url: str | None = None

    # --- Authorship & timing -------------------------------------------
    author: str
    published_at: datetime
    updated_at: datetime | None = None

    # --- Content ---------------------------------------------------------
    title: str | None = None
    content: str = Field(description="Sanitized Markdown/plain-text body.")
    excerpt: str = ""

    # --- Media & links -----------------------------------------------------
    media: list[Media] = Field(default_factory=list)
    links: list[ExternalLink] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[Mention] = Field(default_factory=list)

    # --- Enrichment --------------------------------------------------------
    category: str = "General"
    tags: list[str] = Field(default_factory=list)
    featured: bool = False

    # --- Derived metadata --------------------------------------------------
    language: str | None = None
    word_count: int = 0
    reading_time_minutes: int = 1

    # --- Provenance --------------------------------------------------------
    raw_metadata: dict[str, object] = Field(default_factory=dict)

    @property
    def slug(self) -> str:
        """URL-safe slug derived from the post id."""
        return self.id

    @property
    def year(self) -> int:
        return self.published_at.year

    @property
    def month(self) -> int:
        return self.published_at.month

    @property
    def is_updated(self) -> bool:
        return self.updated_at is not None and self.updated_at != self.published_at
