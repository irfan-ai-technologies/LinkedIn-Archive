"""Media and link models attached to a normalized post."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MediaType(StrEnum):
    """Kind of media attached to a post."""

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    LINK = "link"


class Media(BaseModel):
    """A single media attachment (image, video, document, or external link)."""

    model_config = ConfigDict(frozen=True)

    type: MediaType
    url: str
    title: str | None = None
    alt_text: str | None = None
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None


class ExternalLink(BaseModel):
    """A hyperlink referenced from within a post's text."""

    model_config = ConfigDict(frozen=True)

    url: str
    title: str | None = None
    domain: str | None = None


class Mention(BaseModel):
    """A mention of another person or organization within a post."""

    model_config = ConfigDict(frozen=True)

    name: str
    profile_url: str | None = None
    raw: str = Field(description="The raw @mention text as it appeared in the source content.")
