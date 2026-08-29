"""Persists each provider's raw payload for future reprocessing.

Keeping the untouched provider response on disk (separate from the clean
Markdown in ``content/posts``) means categorization or excerpt logic can be
improved later and re-applied to historical posts without calling the
source API again.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.post import RawPost


class RawArchive:
    def __init__(self, raw_dir: Path | str) -> None:
        self.raw_dir = Path(raw_dir)

    def path_for(self, source: str, source_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in source_id)
        return self.raw_dir / source / f"{safe_id}.json"

    def save(self, raw: RawPost) -> Path:
        path = self.path_for(raw.source, raw.source_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(raw.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def load(self, source: str, source_id: str) -> dict[str, object] | None:
        path = self.path_for(source, source_id)
        if not path.exists():
            return None
        data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        return data
