"""Repository statistics used by ``linkedin-archive stats``."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.models.post import Post


@dataclass(frozen=True)
class ArchiveStats:
    total_posts: int
    by_year: Counter[int]
    by_category: Counter[str]
    by_tag: Counter[str]
    average_word_count: float
    latest_post: Post | None

    def summary_text(self) -> str:
        lines = ["LinkedIn Archive Stats", "", f"Total posts: {self.total_posts}"]
        if self.total_posts == 0:
            return "\n".join(lines)

        lines += ["", "By year:"]
        for year, count in sorted(self.by_year.items(), reverse=True):
            lines.append(f"  {year}: {count}")

        lines += ["", "By category:"]
        for category, count in sorted(self.by_category.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {category}: {count}")

        lines += ["", "Top tags:"]
        for tag, count in self.by_tag.most_common(10):
            lines.append(f"  #{tag}: {count}")

        lines += ["", f"Average post length: {self.average_word_count:.0f} words"]
        if self.latest_post:
            lines.append(
                f"Latest post: {self.latest_post.published_at.date().isoformat()} "
                f"— {self.latest_post.title or self.latest_post.excerpt[:60]}"
            )
        return "\n".join(lines)


def compute_stats(posts: list[Post]) -> ArchiveStats:
    by_year: Counter[int] = Counter(p.year for p in posts)
    by_category: Counter[str] = Counter(p.category for p in posts)
    by_tag: Counter[str] = Counter(tag for p in posts for tag in p.tags)
    average = sum(p.word_count for p in posts) / len(posts) if posts else 0.0
    latest = max(posts, key=lambda p: p.published_at) if posts else None
    return ArchiveStats(
        total_posts=len(posts),
        by_year=by_year,
        by_category=by_category,
        by_tag=by_tag,
        average_word_count=average,
        latest_post=latest,
    )
