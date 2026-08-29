"""Centralized URL scheme for the generated site.

Every generator module builds links through these helpers so the site's
directory layout only needs to change in one place. All paths are root-
relative (start with ``/``) and use trailing-slash "pretty" directories
(``/posts/<id>/`` → ``/posts/<id>/index.html``) for clean GitHub Pages URLs.

Call :func:`configure` once, before generating any pages, with the site's
base path (e.g. ``/LinkedIn-Archive`` for a GitHub Pages project site, or
``""`` when served from the domain root) so every URL below comes out
correct for where the site actually lives.
"""

from __future__ import annotations

from slugify import slugify

_base_path = ""


def configure(base_path: str = "") -> None:
    global _base_path
    _base_path = base_path.rstrip("/")


def _p(path: str) -> str:
    return f"{_base_path}{path}"


def home_url() -> str:
    return _p("/")


def about_url() -> str:
    return _p("/about/")


def post_url(post_id: str) -> str:
    return _p(f"/posts/{slugify(post_id)}/")


def category_index_url() -> str:
    return _p("/categories/")


def category_url(slug: str, page: int = 1) -> str:
    base = f"/categories/{slug}/"
    return _p(base if page <= 1 else f"{base}page/{page}/")


def tag_index_url() -> str:
    return _p("/tags/")


def tag_url(slug: str, page: int = 1) -> str:
    base = f"/tags/{slug}/"
    return _p(base if page <= 1 else f"{base}page/{page}/")


def archive_index_url() -> str:
    return _p("/archive/")


def archive_year_url(year: int, page: int = 1) -> str:
    base = f"/archive/{year}/"
    return _p(base if page <= 1 else f"{base}page/{page}/")


def archive_month_url(year: int, month: int) -> str:
    return _p(f"/archive/{year}/{month:02d}/")


def posts_index_url(page: int = 1) -> str:
    base = "/posts/"
    return _p(base if page <= 1 else f"{base}page/{page}/")


def search_url() -> str:
    return _p("/search/")


def feed_url() -> str:
    return _p("/feed.xml")


def sitemap_url() -> str:
    return _p("/sitemap.xml")


def search_index_url() -> str:
    return _p("/search-index.json")


def static_url(path: str) -> str:
    return _p(f"/static/{path.lstrip('/')}")
