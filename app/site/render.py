"""Safe Markdown → HTML rendering.

Post content originates from an external, untrusted source (LinkedIn, or
whatever a fork owner pastes into a JSON import). It is rendered as Markdown
and then aggressively sanitized: no raw HTML, no scripts, no inline event
handlers, no ``javascript:`` URLs.
"""

from __future__ import annotations

from collections.abc import MutableMapping

import bleach
from bleach.css_sanitizer import CSSSanitizer
from markdown_it import MarkdownIt

_ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "img",
    "span",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]

_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "loading"],
    "span": ["class"],
    "code": ["class"],
}

_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_css_sanitizer = CSSSanitizer(allowed_css_properties=[])

_md = MarkdownIt("commonmark", {"breaks": True, "linkify": True}).enable("linkify")


def render_markdown(text: str) -> str:
    """Render post Markdown to sanitized, safe-to-embed HTML."""
    html = _md.render(text)
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
    )
    return bleach.linkify(
        cleaned,
        callbacks=[*bleach.linkifier.DEFAULT_CALLBACKS, _add_external_link_attrs],
        skip_tags=["pre", "code"],
    )


_LinkAttrs = MutableMapping[tuple[str | None, str], str]


def _add_external_link_attrs(attrs: _LinkAttrs, new: bool = False) -> _LinkAttrs:
    attrs[(None, "rel")] = "nofollow noopener noreferrer"
    attrs[(None, "target")] = "_blank"
    return attrs
