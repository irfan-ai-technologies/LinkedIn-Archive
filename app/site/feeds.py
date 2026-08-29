"""RSS 2.0 feed and XML sitemap generation.

Built by hand with the standard library's XML escaping rather than a
templating engine, so output is guaranteed well-formed and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from app.config import AppConfig
from app.models.post import Post
from app.site.render import render_markdown
from app.site.urls import feed_url, home_url, post_url, sitemap_url


def generate_rss(posts: list[Post], config: AppConfig, *, max_items: int = 30) -> str:
    site = config.user.site
    base_url = config.site_origin
    items = []
    for post in posts[:max_items]:
        link = f"{base_url}{post_url(post.id)}"
        title = escape(post.title or post.excerpt[:60])
        description = escape(render_markdown(post.content))
        items.append(
            "    <item>\n"
            f"      <title>{title}</title>\n"
            f"      <link>{escape(link)}</link>\n"
            f'      <guid isPermaLink="true">{escape(link)}</guid>\n'
            f"      <pubDate>{post.published_at.strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>\n"
            f"      <category>{escape(post.category)}</category>\n"
            f"      <description>{description}</description>\n"
            "    </item>"
        )
    items_xml = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(site.title)}</title>\n"
        f"    <link>{escape(base_url + home_url())}</link>\n"
        f"    <description>{escape(site.description)}</description>\n"
        f"    <language>{escape(site.language)}</language>\n"
        f'    <atom:link href="{escape(base_url)}{feed_url()}" rel="self" '
        'type="application/rss+xml" />\n'
        f"{items_xml}\n"
        "  </channel>\n"
        "</rss>\n"
    )


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str | None = None
    changefreq: str = "monthly"
    priority: str = "0.5"


def generate_sitemap(entries: list[SitemapEntry], config: AppConfig) -> str:
    base_url = config.site_origin
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for entry in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(base_url + entry.loc)}</loc>")
        if entry.lastmod:
            lines.append(f"    <lastmod>{entry.lastmod}</lastmod>")
        lines.append(f"    <changefreq>{entry.changefreq}</changefreq>")
        lines.append(f"    <priority>{entry.priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def generate_robots_txt(config: AppConfig) -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {config.site_origin}{sitemap_url()}\n"
