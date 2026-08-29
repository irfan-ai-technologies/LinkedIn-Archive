"""Static site generation.

Reads normalized posts from :class:`~app.storage.store.PostStore` and
renders the complete site into ``dist/``. This module knows nothing about
LinkedIn, OAuth, or any ingestion provider — it only depends on
:class:`~app.models.post.Post` and the site configuration.
"""

from __future__ import annotations

import calendar
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

from app.config import AppConfig
from app.models.post import Post
from app.models.profile import Profile
from app.search.index import dump_search_index
from app.site.feeds import SitemapEntry, generate_robots_txt, generate_rss, generate_sitemap
from app.site.pagination import paginate
from app.site.render import render_markdown
from app.site.seo import open_graph, post_json_ld, website_json_ld
from app.site.urls import (
    about_url,
    archive_index_url,
    archive_month_url,
    archive_year_url,
    category_index_url,
    category_url,
    feed_url,
    home_url,
    post_url,
    posts_index_url,
    search_index_url,
    search_url,
    sitemap_url,
    tag_index_url,
    tag_url,
)
from app.storage.profile_store import load_profile
from app.storage.store import PostStore


@dataclass(frozen=True)
class CategoryInfo:
    name: str
    slug: str
    description: str
    count: int


@dataclass(frozen=True)
class TagInfo:
    slug: str
    count: int


def _format_date(value: datetime) -> str:
    return f"{value:%B} {value.day}, {value:%Y}"


class SiteGenerator:
    """Renders the full static site from normalized content into ``dist/``."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = PostStore(config.posts_dir)
        self.env = self._build_environment()

    def _build_environment(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(str(self.config.templates_dir)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["render_markdown"] = render_markdown
        env.filters["format_date"] = _format_date
        env.globals.update(
            {
                "site": self.config.user.site,
                "theme": self.config.user.theme,
                "config": self.config,
                "home_url": home_url,
                "about_url": about_url,
                "post_url": post_url,
                "posts_index_url": posts_index_url,
                "category_index_url": category_index_url,
                "category_url": category_url,
                "tag_index_url": tag_index_url,
                "tag_url": tag_url,
                "archive_index_url": archive_index_url,
                "archive_year_url": archive_year_url,
                "archive_month_url": archive_month_url,
                "search_url": search_url,
                "feed_url": feed_url,
                "sitemap_url": sitemap_url,
                "search_index_url": search_index_url,
                "open_graph": open_graph,
                "post_json_ld": post_json_ld,
                "website_json_ld": website_json_ld,
            }
        )
        return env

    # -- Public API -----------------------------------------------------

    def generate(self) -> Path:
        posts = self.store.load_all()
        profile = load_profile(self.config.profile_path)

        if self.config.dist_dir.exists():
            shutil.rmtree(self.config.dist_dir)
        self.config.dist_dir.mkdir(parents=True)

        category_slug_map, categories = self._build_categories(posts)
        tags = self._build_tags(posts)
        self.env.globals["category_slug_map"] = category_slug_map
        self.env.globals["profile"] = self._profile_context(profile)
        self.env.globals["profile_footer_year"] = max(
            (p.year for p in posts), default=datetime.now(tz=UTC).year
        )

        self._write_home(posts, categories, tags)
        self._write_about()
        self._write_posts(posts, category_slug_map)
        self._write_posts_index(posts)
        self._write_categories(posts, categories)
        self._write_tags(posts, tags)
        self._write_archive(posts)
        self._write_search_page(posts)
        self._write_404()
        self._write_feeds(posts)
        self._write_search_index(posts)
        self._copy_static()

        return self.config.dist_dir

    # -- Helpers ----------------------------------------------------------

    def _profile_context(self, profile: Profile) -> dict[str, object]:
        data = profile.model_dump()
        data["bio_html"] = render_markdown(profile.bio)
        return data

    def _build_categories(self, posts: list[Post]) -> tuple[dict[str, str], list[CategoryInfo]]:
        configured = {c.name: c for c in self.config.user.sorted_categories()}
        counts: dict[str, int] = {}
        for post in posts:
            counts[post.category] = counts.get(post.category, 0) + 1

        slug_map: dict[str, str] = {}
        infos: list[CategoryInfo] = []
        seen_names = set(configured) | set(counts)
        for name in seen_names:
            cfg = configured.get(name)
            slug = cfg.slug if cfg else slugify(name)
            slug_map[name] = slug
            infos.append(
                CategoryInfo(
                    name=name,
                    slug=slug,
                    description=cfg.description if cfg else "",
                    count=counts.get(name, 0),
                )
            )
        infos.sort(key=lambda c: (-c.count, c.name))
        return slug_map, infos

    def _build_tags(self, posts: list[Post]) -> list[TagInfo]:
        counts: dict[str, int] = {}
        for post in posts:
            for tag in post.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagInfo(slug=slug, count=count) for slug, count in sorted(counts.items())]

    def _render(self, template_name: str, out_path: Path, **context: object) -> None:
        template = self.env.get_template(template_name)
        html = template.render(**context)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")

    # -- Pages ------------------------------------------------------------

    def _write_home(
        self, posts: list[Post], categories: list[CategoryInfo], tags: list[TagInfo]
    ) -> None:
        theme = self.config.user.theme
        featured = [p for p in posts if p.featured][: theme.featured_count]
        recent = posts[: theme.recent_count]
        popular_tags = sorted(tags, key=lambda t: (-t.count, t.slug))[:12]
        self._render(
            "pages/home.html",
            self.config.dist_dir / "index.html",
            canonical_path=home_url(),
            featured_posts=featured,
            recent_posts=recent,
            categories=categories,
            popular_tags=popular_tags,
        )

    def _write_about(self) -> None:
        self._render(
            "pages/about.html",
            self.config.dist_dir / "about" / "index.html",
            canonical_path=about_url(),
        )

    def _write_posts(self, posts: list[Post], category_slug_map: dict[str, str]) -> None:
        for index, post in enumerate(posts):
            previous_post = posts[index + 1] if index + 1 < len(posts) else None
            next_post = posts[index - 1] if index > 0 else None
            related = [p for p in posts if p.id != post.id and p.category == post.category][:3]
            self._render(
                "pages/post.html",
                self.config.dist_dir / "posts" / slugify(post.id) / "index.html",
                canonical_path=post_url(post.id),
                post=post,
                previous_post=previous_post,
                next_post=next_post,
                related_posts=related,
            )

    def _write_posts_index(self, posts: list[Post]) -> None:
        per_page = self.config.user.pagination.posts_per_page
        pages = paginate(posts, per_page)
        for page in pages:
            out = (
                self.config.dist_dir / "posts" / "index.html"
                if page.page_number == 1
                else self.config.dist_dir / "posts" / "page" / str(page.page_number) / "index.html"
            )
            self._render(
                "pages/posts_index.html",
                out,
                canonical_path=posts_index_url(page.page_number),
                page=page,
                total_count=len(posts),
                url_for_page=lambda n: posts_index_url(n),
            )

    def _write_categories(self, posts: list[Post], categories: list[CategoryInfo]) -> None:
        self._render(
            "pages/category_index.html",
            self.config.dist_dir / "categories" / "index.html",
            canonical_path=category_index_url(),
            categories=categories,
        )
        per_page = self.config.user.pagination.posts_per_page
        for category in categories:
            category_posts = [p for p in posts if p.category == category.name]
            pages = paginate(category_posts, per_page)
            for page in pages:
                out = (
                    self.config.dist_dir / "categories" / category.slug / "index.html"
                    if page.page_number == 1
                    else self.config.dist_dir
                    / "categories"
                    / category.slug
                    / "page"
                    / str(page.page_number)
                    / "index.html"
                )
                self._render(
                    "pages/category.html",
                    out,
                    canonical_path=category_url(category.slug, page.page_number),
                    category=category,
                    page=page,
                    total_count=len(category_posts),
                    url_for_page=lambda n, slug=category.slug: category_url(slug, n),
                )

    def _write_tags(self, posts: list[Post], tags: list[TagInfo]) -> None:
        self._render(
            "pages/tag_index.html",
            self.config.dist_dir / "tags" / "index.html",
            canonical_path=tag_index_url(),
            tags=tags,
        )
        per_page = self.config.user.pagination.posts_per_page
        for tag in tags:
            tag_posts = [p for p in posts if tag.slug in p.tags]
            pages = paginate(tag_posts, per_page)
            for page in pages:
                out = (
                    self.config.dist_dir / "tags" / tag.slug / "index.html"
                    if page.page_number == 1
                    else self.config.dist_dir
                    / "tags"
                    / tag.slug
                    / "page"
                    / str(page.page_number)
                    / "index.html"
                )
                self._render(
                    "pages/tag.html",
                    out,
                    canonical_path=tag_url(tag.slug, page.page_number),
                    tag_slug=tag.slug,
                    page=page,
                    total_count=len(tag_posts),
                    url_for_page=lambda n, slug=tag.slug: tag_url(slug, n),
                )

    def _write_archive(self, posts: list[Post]) -> None:
        by_year: dict[int, list[Post]] = {}
        for post in posts:
            by_year.setdefault(post.year, []).append(post)

        years_context = []
        for year in sorted(by_year, reverse=True):
            year_posts = by_year[year]
            by_month: dict[int, list[Post]] = {}
            for post in year_posts:
                by_month.setdefault(post.month, []).append(post)
            months = [
                (month, calendar.month_name[month], len(by_month[month]))
                for month in sorted(by_month, reverse=True)
            ]
            years_context.append((year, len(year_posts), months))

            per_page = self.config.user.pagination.archive_per_page
            pages = paginate(year_posts, per_page)
            for page in pages:
                out = (
                    self.config.dist_dir / "archive" / str(year) / "index.html"
                    if page.page_number == 1
                    else self.config.dist_dir
                    / "archive"
                    / str(year)
                    / "page"
                    / str(page.page_number)
                    / "index.html"
                )
                self._render(
                    "pages/archive_year.html",
                    out,
                    canonical_path=archive_year_url(year, page.page_number),
                    year=year,
                    page=page,
                    total_count=len(year_posts),
                    url_for_page=lambda n, y=year: archive_year_url(y, n),
                )

            for month, month_posts in by_month.items():
                self._render(
                    "pages/archive_month.html",
                    self.config.dist_dir / "archive" / str(year) / f"{month:02d}" / "index.html",
                    canonical_path=archive_month_url(year, month),
                    year=year,
                    month=month,
                    month_name=calendar.month_name[month],
                    posts=month_posts,
                )

        self._render(
            "pages/archive_index.html",
            self.config.dist_dir / "archive" / "index.html",
            canonical_path=archive_index_url(),
            years=years_context,
        )

    def _write_search_page(self, posts: list[Post]) -> None:
        self._render(
            "pages/search.html",
            self.config.dist_dir / "search" / "index.html",
            canonical_path=search_url(),
            total_count=len(posts),
        )

    def _write_404(self) -> None:
        self._render(
            "pages/404.html", self.config.dist_dir / "404.html", canonical_path="/404.html"
        )

    def _write_feeds(self, posts: list[Post]) -> None:
        (self.config.dist_dir / "feed.xml").write_text(
            generate_rss(posts, self.config), encoding="utf-8"
        )

        entries = [SitemapEntry(loc=home_url(), priority="1.0"), SitemapEntry(loc=about_url())]
        entries.append(SitemapEntry(loc=posts_index_url()))
        entries.append(SitemapEntry(loc=category_index_url()))
        entries.append(SitemapEntry(loc=tag_index_url()))
        entries.append(SitemapEntry(loc=archive_index_url()))
        entries.append(SitemapEntry(loc=search_url()))
        for post in posts:
            lastmod = (post.updated_at or post.published_at).date().isoformat()
            entries.append(
                SitemapEntry(
                    loc=post_url(post.id), lastmod=lastmod, changefreq="yearly", priority="0.7"
                )
            )

        (self.config.dist_dir / "sitemap.xml").write_text(
            generate_sitemap(entries, self.config), encoding="utf-8"
        )
        (self.config.dist_dir / "robots.txt").write_text(
            generate_robots_txt(self.config), encoding="utf-8"
        )

    def _write_search_index(self, posts: list[Post]) -> None:
        content = dump_search_index(
            posts, max_indexed_chars=self.config.user.search.max_indexed_chars
        )
        (self.config.dist_dir / "search-index.json").write_text(content, encoding="utf-8")

    def _copy_static(self) -> None:
        static_src = self.config.static_dir
        if not static_src.exists():
            return
        shutil.copytree(static_src, self.config.dist_dir / "static", dirs_exist_ok=True)


def build_site(config: AppConfig) -> Path:
    return SiteGenerator(config).generate()
