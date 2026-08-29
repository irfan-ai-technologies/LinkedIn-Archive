"""Centralized URL scheme for the generated site.

Every generator module builds links through these helpers so the site's
directory layout only needs to change in one place. All paths are root-
relative (start with ``/``) and use trailing-slash "pretty" directories
(``/posts/<id>/`` → ``/posts/<id>/index.html``) for clean GitHub Pages URLs.
"""

from __future__ import annotations

from slugify import slugify


def home_url() -> str:
    return "/"


def about_url() -> str:
    return "/about/"


def post_url(post_id: str) -> str:
    return f"/posts/{slugify(post_id)}/"


def category_index_url() -> str:
    return "/categories/"


def category_url(slug: str, page: int = 1) -> str:
    base = f"/categories/{slug}/"
    return base if page <= 1 else f"{base}page/{page}/"


def tag_index_url() -> str:
    return "/tags/"


def tag_url(slug: str, page: int = 1) -> str:
    base = f"/tags/{slug}/"
    return base if page <= 1 else f"{base}page/{page}/"


def archive_index_url() -> str:
    return "/archive/"


def archive_year_url(year: int, page: int = 1) -> str:
    base = f"/archive/{year}/"
    return base if page <= 1 else f"{base}page/{page}/"


def archive_month_url(year: int, month: int) -> str:
    return f"/archive/{year}/{month:02d}/"


def posts_index_url(page: int = 1) -> str:
    base = "/posts/"
    return base if page <= 1 else f"{base}page/{page}/"


def search_url() -> str:
    return "/search/"


def feed_url() -> str:
    return "/feed.xml"


def sitemap_url() -> str:
    return "/sitemap.xml"


def search_index_url() -> str:
    return "/search-index.json"
