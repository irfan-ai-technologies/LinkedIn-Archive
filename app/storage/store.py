"""Reads and writes normalized posts as Markdown files under ``content/posts``."""

from __future__ import annotations

from pathlib import Path

from slugify import slugify

from app.models.post import Post
from app.storage.frontmatter import FrontMatterError, markdown_to_post, post_to_markdown


class PostStore:
    """Filesystem-backed store for enriched :class:`Post` objects."""

    def __init__(self, posts_dir: Path | str) -> None:
        self.posts_dir = Path(posts_dir)

    def path_for(self, post_id: str) -> Path:
        return self.posts_dir / f"{slugify(post_id)}.md"

    def exists(self, post_id: str) -> bool:
        return self.path_for(post_id).exists()

    def get(self, post_id: str) -> Post | None:
        path = self.path_for(post_id)
        if not path.exists():
            return None
        return markdown_to_post(path.read_text(encoding="utf-8"))

    def save(self, post: Post) -> Path:
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(post.id)
        path.write_text(post_to_markdown(post), encoding="utf-8")
        return path

    def delete(self, post_id: str) -> None:
        path = self.path_for(post_id)
        if path.exists():
            path.unlink()

    def load_all(self) -> list[Post]:
        if not self.posts_dir.exists():
            return []
        posts: list[Post] = []
        for path in sorted(self.posts_dir.glob("*.md")):
            try:
                posts.append(markdown_to_post(path.read_text(encoding="utf-8")))
            except FrontMatterError:
                continue
        return sorted(posts, key=lambda p: p.published_at, reverse=True)

    def all_ids_for_source(self, source: str) -> set[str]:
        return {p.id for p in self.load_all() if p.source == source}
