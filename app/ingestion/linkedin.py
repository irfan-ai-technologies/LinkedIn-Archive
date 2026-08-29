"""LinkedIn API content provider.

Uses LinkedIn's official REST API only (never scraping, never a headless
browser, never stored credentials beyond an OAuth token). All LinkedIn API
endpoint paths, versions, and payload-shape assumptions are isolated to this
module so that a future LinkedIn API change only requires editing this one
file. See ``docs/linkedin-api.md`` for the permissions this requires and how
to request them.

Reading a member's own posts requires LinkedIn's restricted member-social
products (for example ``r_member_social``). Until your app has been
approved for that, :meth:`LinkedInProvider.fetch_posts` will fail with a
clear :class:`~app.ingestion.base.ProviderError` — use the sample or import
provider in the meantime.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.ingestion.base import ProviderError
from app.ingestion.linkedin_oauth import LinkedInAuthError, TokenSet, refresh_access_token
from app.ingestion.normalize import extract_hashtags, extract_links, guess_language
from app.models.media import Media, MediaType
from app.models.post import RawPost

PROVIDER_NAME = "linkedin"

API_BASE = "https://api.linkedin.com/rest"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# LinkedIn requires an explicit version header on REST API calls
# (YYYYMM format). Bump this periodically per LinkedIn's versioning docs:
# https://learn.microsoft.com/en-us/linkedin/marketing/versioning
API_VERSION = "202405"

_MEDIA_TYPE_MAP = {
    "IMAGE": MediaType.IMAGE,
    "VIDEO": MediaType.VIDEO,
    "DOCUMENT": MediaType.DOCUMENT,
    "ARTICLE": MediaType.LINK,
}


class LinkedInProvider:
    """Fetches the authenticated member's own posts via LinkedIn's Posts API."""

    name = PROVIDER_NAME

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        tokens: TokenSet,
        on_token_refresh: Any = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._tokens = tokens
        self._on_token_refresh = on_token_refresh
        self._http = http_client or httpx.Client(timeout=30.0)

    def _ensure_fresh_token(self) -> str:
        if self._tokens.is_expired:
            if not self._tokens.refresh_token:
                raise ProviderError(
                    self.name,
                    "access token expired and no refresh token is available; "
                    "run `linkedin-archive auth login` again",
                )
            try:
                self._tokens = refresh_access_token(
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    refresh_token=self._tokens.refresh_token,
                    client=self._http,
                )
            except LinkedInAuthError as exc:
                raise ProviderError(self.name, str(exc)) from exc
            if self._on_token_refresh:
                self._on_token_refresh(self._tokens)
        return self._tokens.access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_fresh_token()}",
            "LinkedIn-Version": API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _member_urn(self) -> str:
        response = self._http.get(USERINFO_URL, headers=self._headers())
        if response.status_code != 200:
            raise ProviderError(
                self.name, f"failed to resolve member identity (HTTP {response.status_code})"
            )
        member_id = response.json().get("sub")
        if not member_id:
            raise ProviderError(self.name, "userinfo response did not include a member id")
        return f"urn:li:person:{member_id}"

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        author_urn = self._member_urn()
        posts: list[RawPost] = []
        start = 0
        page_size = 50

        while True:
            response = self._http.get(
                f"{API_BASE}/posts",
                headers=self._headers(),
                params={"author": author_urn, "q": "author", "count": page_size, "start": start},
            )
            if response.status_code == 403:
                raise ProviderError(
                    self.name,
                    "LinkedIn returned 403 Forbidden. Your app most likely has not been "
                    "approved for member-social read permissions (e.g. r_member_social). "
                    "See docs/linkedin-api.md.",
                )
            if response.status_code != 200:
                raise ProviderError(self.name, f"LinkedIn API returned HTTP {response.status_code}")

            payload = response.json()
            elements = payload.get("elements", [])
            for element in elements:
                raw = self._normalize_element(element)
                if since is not None and raw.published_at < since:
                    return posts
                posts.append(raw)

            total = payload.get("paging", {}).get("total", start + len(elements))
            start += len(elements)
            if not elements or start >= total:
                break

        return posts

    def _normalize_element(self, element: dict[str, Any]) -> RawPost:
        post_id = str(element.get("id", ""))
        text = _extract_commentary(element)
        published_ms = element.get("publishedAt") or element.get("createdAt") or 0
        updated_ms = element.get("lastModifiedAt")

        media = _extract_media(element)
        hashtags = extract_hashtags(text)
        links = extract_links(text)

        return RawPost(
            id=f"linkedin-{_urn_to_id(post_id)}",
            source=PROVIDER_NAME,
            source_id=post_id,
            source_url=_activity_url(post_id),
            author=str(element.get("author", "")),
            published_at=_ms_to_datetime(published_ms),
            updated_at=_ms_to_datetime(updated_ms) if updated_ms else None,
            text=text,
            media=media,
            links=links,
            hashtags=hashtags,
            language=guess_language(text),
            raw_metadata=element,
        )


def _extract_commentary(element: dict[str, Any]) -> str:
    commentary = element.get("commentary")
    if isinstance(commentary, str):
        return commentary
    if isinstance(commentary, dict):
        return str(commentary.get("text", ""))
    return ""


def _extract_media(element: dict[str, Any]) -> list[Media]:
    content = element.get("content")
    if not isinstance(content, dict):
        return []
    media_items: list[Media] = []
    for kind in ("media", "multiImage", "article"):
        node = content.get(kind)
        if node is None:
            continue
        entries = node.get("images") if isinstance(node, dict) and "images" in node else [node]
        for entry in entries if isinstance(entries, list) else [entries]:
            if not isinstance(entry, dict):
                continue
            media_type = _MEDIA_TYPE_MAP.get(
                str(entry.get("mediaType", kind)).upper(), MediaType.LINK
            )
            url = entry.get("originalUrl") or entry.get("url") or entry.get("id", "")
            if not url:
                continue
            media_items.append(
                Media(
                    type=media_type,
                    url=str(url),
                    title=entry.get("title"),
                    alt_text=entry.get("altText"),
                )
            )
    return media_items


def _urn_to_id(urn: str) -> str:
    return urn.rsplit(":", 1)[-1] if ":" in urn else urn


def _activity_url(urn: str) -> str | None:
    activity_id = _urn_to_id(urn)
    if not activity_id:
        return None
    return f"https://www.linkedin.com/feed/update/{urn}" if urn.startswith("urn:") else None


def _ms_to_datetime(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)
