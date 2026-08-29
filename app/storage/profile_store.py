"""Loads the site owner's profile from ``content/profile/profile.yaml``."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.models.profile import Profile


def load_profile(path: Path | str) -> Profile:
    path = Path(path)
    if not path.exists():
        return Profile(name="Anonymous", headline="", bio="")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Profile.model_validate(data)
