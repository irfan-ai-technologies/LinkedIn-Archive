"""Header-matching helpers shared by providers that read LinkedIn's CSV
data-export files.

LinkedIn has changed column names/casing across export format revisions, so
every lookup here is case- and punctuation-insensitive and matches against a
list of known aliases rather than a single exact header.
"""

from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def normalize_header(name: str) -> str:
    """Collapse a CSV header to a comparable form: lowercase, no punctuation/spaces."""
    return _NON_ALNUM_RE.sub("", name.strip().lower())


def find_column(fieldnames: list[str], *aliases: str) -> str | None:
    """Return the first fieldname matching any of ``aliases``, or ``None``."""
    normalized = {normalize_header(f): f for f in fieldnames}
    for alias in aliases:
        match = normalized.get(normalize_header(alias))
        if match is not None:
            return match
    return None
