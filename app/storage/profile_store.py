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


def save_profile(path: Path | str, profile: Profile) -> None:
    """Write ``profile`` back to ``path`` as YAML.

    Field order follows the model's declaration order (``sort_keys=False``),
    which is deterministic across runs — required for reproducible builds.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
