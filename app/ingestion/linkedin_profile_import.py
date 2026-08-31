"""LinkedIn personal data-export importer (Profile -> About page).

Reads ``Profile.csv`` from LinkedIn's "Download my data" export (the
**Profile** checkbox) and produces the fields needed to populate
``content/profile/profile.yaml`` — the file that already drives both the
About page and the home-page bio (see ``app/storage/profile_store.py`` and
``app/site/generator.py``). Fields the export doesn't carry at all (avatar,
social links) are never touched; see :func:`merge_profile`.

Like ``app/ingestion/linkedin_export.py``, this only reads a file LinkedIn
already handed the member directly — no scraping, no API calls.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.base import ProviderError
from app.ingestion.csv_utils import find_column
from app.models.profile import Profile

PROVIDER_NAME = "linkedin_profile_import"

_FIRST_NAME_ALIASES = ("First Name",)
_LAST_NAME_ALIASES = ("Last Name",)
_HEADLINE_ALIASES = ("Headline",)
_SUMMARY_ALIASES = ("Summary",)
_LOCATION_ALIASES = ("Geo Location", "Location")


@dataclass(frozen=True)
class ProfileImportFields:
    """Fields recovered from ``Profile.csv``; ``None`` means "not present in the file"."""

    name: str | None
    headline: str | None
    bio: str | None
    location: str | None


def _cell(row: dict[str, str], column: str | None) -> str:
    if column is None:
        return ""
    return (row.get(column) or "").strip()


def parse_profile_csv(path: Path | str) -> ProfileImportFields:
    path = Path(path)
    if not path.exists():
        raise ProviderError(PROVIDER_NAME, f"Profile.csv not found: {path}")

    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ProviderError(PROVIDER_NAME, f"{path} has no header row")
            fields = list(reader.fieldnames)
            row = next(reader, None)
    except OSError as exc:
        raise ProviderError(PROVIDER_NAME, f"could not read {path}: {exc}") from exc
    except csv.Error as exc:
        raise ProviderError(PROVIDER_NAME, f"invalid CSV in {path}: {exc}") from exc

    if row is None:
        raise ProviderError(PROVIDER_NAME, f"{path} has a header row but no data row")

    first = _cell(row, find_column(fields, *_FIRST_NAME_ALIASES))
    last = _cell(row, find_column(fields, *_LAST_NAME_ALIASES))
    name = f"{first} {last}".strip() or None
    headline = _cell(row, find_column(fields, *_HEADLINE_ALIASES)) or None
    bio = _cell(row, find_column(fields, *_SUMMARY_ALIASES)) or None
    location = _cell(row, find_column(fields, *_LOCATION_ALIASES)) or None

    if name is None and headline is None and bio is None and location is None:
        raise ProviderError(
            PROVIDER_NAME,
            f"{path} doesn't have any recognizable profile column — "
            f"headers found: {sorted(fields)}",
        )

    return ProfileImportFields(name=name, headline=headline, bio=bio, location=location)


def merge_profile(existing: Profile, parsed: ProfileImportFields) -> Profile:
    """Overlay fields found in ``parsed`` onto ``existing``.

    Only ``name``, ``headline``, ``bio``, and ``location`` can come from a
    LinkedIn export; ``avatar`` and ``links`` are always carried over
    unchanged from ``existing`` since the export has no equivalent data.
    """
    updates: dict[str, str] = {}
    if parsed.name is not None:
        updates["name"] = parsed.name
    if parsed.headline is not None:
        updates["headline"] = parsed.headline
    if parsed.bio is not None:
        updates["bio"] = parsed.bio
    if parsed.location is not None:
        updates["location"] = parsed.location
    return existing.model_copy(update=updates)
