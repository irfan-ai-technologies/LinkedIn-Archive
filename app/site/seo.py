"""SEO metadata: OpenGraph, Twitter cards, and JSON-LD structured data."""

from __future__ import annotations

from app.config import AppConfig
from app.models.post import Post
from app.site.urls import post_url


def post_json_ld(post: Post, config: AppConfig) -> dict[str, object]:
    base_url = config.site_url
    data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.title or post.excerpt[:110],
        "description": post.excerpt,
        "datePublished": post.published_at.isoformat(),
        "author": {"@type": "Person", "name": post.author},
        "url": f"{base_url}{post_url(post.id)}",
        "keywords": ", ".join(post.tags) if post.tags else post.category,
        "articleSection": post.category,
    }
    if post.updated_at:
        data["dateModified"] = post.updated_at.isoformat()
    if post.media:
        images = [m.url for m in post.media if m.type == "image"]
        if images:
            data["image"] = images
    return data


def website_json_ld(config: AppConfig) -> dict[str, object]:
    site = config.user.site
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site.title,
        "description": site.description,
        "url": config.site_url,
    }


def open_graph(
    *, title: str, description: str, url: str, config: AppConfig, og_type: str = "website"
) -> dict[str, str]:
    return {
        "og:site_name": config.user.site.title,
        "og:type": og_type,
        "og:title": title,
        "og:description": description,
        "og:url": f"{config.site_url}{url}",
        "twitter:card": "summary",
        "twitter:title": title,
        "twitter:description": description,
    }
