"""Author/profile model used to render the About page."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileLinks(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    email: str | None = None


class Profile(BaseModel):
    """The site owner's profile, loaded from ``content/profile/profile.yaml``."""

    name: str
    headline: str = ""
    bio: str = ""
    avatar: str | None = None
    location: str | None = None
    links: ProfileLinks = Field(default_factory=ProfileLinks)
