"""Repository validation used by ``linkedin-archive validate``.

Checks content and configuration for problems that would otherwise only
surface as a broken build or a broken page: malformed front matter, broken
internal links, duplicate IDs, invalid dates, missing required metadata,
unknown categories, and malformed configuration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.config import AppConfig
from app.storage.frontmatter import FrontMatterError, markdown_to_post


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary_text(self) -> str:
        lines = ["LinkedIn Archive Validation", ""]
        if not self.errors and not self.warnings:
            lines.append("No issues found.")
            return "\n".join(lines)
        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            lines += [f"  - {e}" for e in self.errors]
        if self.warnings:
            if self.errors:
                lines.append("")
            lines.append(f"Warnings ({len(self.warnings)}):")
            lines += [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


def validate_repository(config: AppConfig) -> ValidationReport:
    report = ValidationReport()

    known_category_names = {c.name for c in config.user.categories} | {"General"}
    known_category_slugs = [c.slug for c in config.user.categories]
    if len(known_category_slugs) != len(set(known_category_slugs)):
        report.errors.append("configuration: duplicate category slugs in config.yaml")

    posts_dir = config.posts_dir
    if not posts_dir.exists():
        report.warnings.append(f"content: posts directory does not exist: {posts_dir}")
        return report

    seen_ids: dict[str, str] = {}
    all_posts = {}

    for path in sorted(posts_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            post = markdown_to_post(text)
        except FrontMatterError as exc:
            report.errors.append(f"{path.name}: {exc}")
            continue

        if post.id in seen_ids:
            report.errors.append(
                f"{path.name}: duplicate post id {post.id!r} (already used by {seen_ids[post.id]})"
            )
        else:
            seen_ids[post.id] = path.name
            all_posts[post.id] = post

        if not isinstance(post.published_at, datetime):
            report.errors.append(f"{path.name}: published_at is not a valid date")
        elif post.published_at > datetime.now(tz=post.published_at.tzinfo or UTC) + timedelta(
            days=1
        ):
            report.warnings.append(f"{path.name}: published_at is in the future")

        if post.category not in known_category_names:
            report.warnings.append(
                f"{path.name}: category {post.category!r} is not defined in config.yaml"
            )

        if post.source_url and not post.source_url.startswith(("http://", "https://")):
            report.warnings.append(f"{path.name}: source_url does not look like a URL")

        if not post.content.strip():
            report.warnings.append(f"{path.name}: post body is empty")

    known_post_ids = set(all_posts)
    base_url = config.site_url
    for post_id, post in all_posts.items():
        for candidate in _internal_link_targets(post.content, base_url):
            if candidate not in known_post_ids:
                report.errors.append(
                    f"{seen_ids[post_id]}: broken internal link to post {candidate!r}"
                )

    return report


def _internal_link_targets(content: str, base_url: str) -> list[str]:
    """Extract post ids referenced by internal ``/posts/<id>/`` links in content."""
    targets = []
    pattern = re.compile(re.escape(base_url) + r"/posts/([a-z0-9-]+)/?" if base_url else r"(?!)")
    for match in pattern.finditer(content):
        targets.append(match.group(1))
    for match in re.finditer(r"(?<!\w)/posts/([a-z0-9-]+)/", content):
        targets.append(match.group(1))
    return targets
