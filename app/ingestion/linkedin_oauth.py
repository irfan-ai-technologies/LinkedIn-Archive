"""LinkedIn OAuth 2.0 (Authorization Code flow).

This module implements *only* the official OAuth mechanism documented at
https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow.
No credentials are ever scraped or hardcoded. Reading a member's own posts
requires LinkedIn's restricted member-social-read permissions (for example
``r_member_social``), which require LinkedIn's app review/approval — see
``docs/linkedin-api.md``. This module does not attempt to work around that;
if the required product/scope hasn't been granted, LinkedIn's API will
reject the request and :class:`LinkedInAuthError` surfaces that clearly.

Tokens are never written into the repository or into generated content.
They are persisted to a JSON file *outside* version control (see
``AppConfig.secrets.linkedin_token_store``, default ``.secrets/``, which is
gitignored) and are never logged.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Scopes required to read the authenticated member's own posts. Sharing/social
# scopes are restricted products on LinkedIn and require approval; requesting
# them here does not grant access on its own. See docs/linkedin-api.md.
DEFAULT_SCOPES = ("openid", "profile", "r_member_social")


class LinkedInAuthError(RuntimeError):
    """Raised for any OAuth failure. Never includes secret values in its message."""


@dataclass
class TokenSet:
    access_token: str
    expires_at: float
    refresh_token: str | None = None
    refresh_token_expires_at: float | None = None
    scope: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() >= (self.expires_at - 60)

    def to_dict(self) -> dict[str, object]:
        return {
            "access_token": self.access_token,
            "expires_at": self.expires_at,
            "refresh_token": self.refresh_token,
            "refresh_token_expires_at": self.refresh_token_expires_at,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TokenSet:
        return cls(
            access_token=str(data["access_token"]),
            expires_at=float(data["expires_at"]),  # type: ignore[arg-type]
            refresh_token=data.get("refresh_token"),  # type: ignore[arg-type]
            refresh_token_expires_at=data.get("refresh_token_expires_at"),  # type: ignore[arg-type]
            scope=str(data.get("scope", "")),
        )


class TokenStore:
    """Persists a :class:`TokenSet` to a local file outside the repository."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> TokenSet | None:
        if not self.path.exists():
            return None
        try:
            return TokenSet.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def save(self, tokens: TokenSet) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(tokens.to_dict(), indent=2), encoding="utf-8")
        self.path.chmod(0o600)


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    state: str | None = None,
) -> tuple[str, str]:
    """Build the URL to send the user's browser to. Returns ``(url, state)``."""
    state = state or secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(scopes),
    }
    query = httpx.QueryParams(params)
    return f"{AUTHORIZATION_URL}?{query}", state


def exchange_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    client: httpx.Client | None = None,
) -> TokenSet:
    """Exchange an authorization code for an access (and possibly refresh) token."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        response = client.post(TOKEN_URL, data=data)
    finally:
        if owns_client:
            client.close()
    return _token_set_from_response(response)


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    client: httpx.Client | None = None,
) -> TokenSet:
    """Exchange a refresh token for a new access token.

    LinkedIn only issues refresh tokens to applications approved for
    ``offline_access``. If your app was not granted that product, re-run
    ``linkedin-archive auth login`` when the access token expires instead.
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        response = client.post(TOKEN_URL, data=data)
    finally:
        if owns_client:
            client.close()
    return _token_set_from_response(response)


def _token_set_from_response(response: httpx.Response) -> TokenSet:
    if response.status_code != 200:
        # Deliberately do not include request body/headers, which may echo
        # back the client secret.
        raise LinkedInAuthError(
            f"LinkedIn token endpoint returned HTTP {response.status_code}. "
            "Check LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET / LINKEDIN_REDIRECT_URI "
            "and that your app has been granted the required product."
        )
    payload = response.json()
    now = time.time()
    expires_in = float(payload.get("expires_in", 3600))
    refresh_expires_in = payload.get("refresh_token_expires_in")
    return TokenSet(
        access_token=payload["access_token"],
        expires_at=now + expires_in,
        refresh_token=payload.get("refresh_token"),
        refresh_token_expires_at=(now + float(refresh_expires_in)) if refresh_expires_in else None,
        scope=payload.get("scope", ""),
    )
