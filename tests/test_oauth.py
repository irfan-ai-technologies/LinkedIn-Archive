import time
from pathlib import Path

import httpx
import pytest
import respx

from app.ingestion.linkedin_oauth import (
    LinkedInAuthError,
    TokenSet,
    TokenStore,
    build_authorization_url,
    exchange_code_for_token,
    refresh_access_token,
)


def test_build_authorization_url_contains_required_params() -> None:
    url, state = build_authorization_url(
        client_id="client-123", redirect_uri="http://localhost:8765/callback"
    )
    assert "client_id=client-123" in url
    assert "response_type=code" in url
    assert f"state={state}" in url
    assert "r_member_social" in url


def test_build_authorization_url_uses_provided_state() -> None:
    url, state = build_authorization_url(
        client_id="client-123", redirect_uri="http://localhost/cb", state="fixed-state"
    )
    assert state == "fixed-state"
    assert "state=fixed-state" in url


@respx.mock
def test_exchange_code_for_token_success() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(
            200, json={"access_token": "tok-1", "expires_in": 3600, "scope": "openid"}
        )
    )
    tokens = exchange_code_for_token(
        client_id="id", client_secret="secret", redirect_uri="http://localhost/cb", code="abc"
    )
    assert tokens.access_token == "tok-1"
    assert not tokens.is_expired


@respx.mock
def test_exchange_code_for_token_failure_raises_without_leaking_secret() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(LinkedInAuthError) as exc_info:
        exchange_code_for_token(
            client_id="id",
            client_secret="super-secret",
            redirect_uri="http://localhost/cb",
            code="bad",
        )
    assert "super-secret" not in str(exc_info.value)


@respx.mock
def test_refresh_access_token_success() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(200, json={"access_token": "tok-2", "expires_in": 3600})
    )
    tokens = refresh_access_token(client_id="id", client_secret="secret", refresh_token="refresh-1")
    assert tokens.access_token == "tok-2"


def test_token_set_is_expired() -> None:
    expired = TokenSet(access_token="a", expires_at=time.time() - 10)
    assert expired.is_expired
    fresh = TokenSet(access_token="a", expires_at=time.time() + 3600)
    assert not fresh.is_expired


def test_token_store_round_trip(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "secrets" / "token.json")
    tokens = TokenSet(access_token="a", expires_at=time.time() + 3600, refresh_token="r")
    store.save(tokens)
    loaded = store.load()
    assert loaded is not None
    assert loaded.access_token == "a"
    assert loaded.refresh_token == "r"


def test_token_store_missing_file_returns_none(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "missing.json")
    assert store.load() is None


def test_token_store_file_is_private(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token.json")
    store.save(TokenSet(access_token="a", expires_at=time.time() + 3600))
    mode = (tmp_path / "token.json").stat().st_mode & 0o777
    assert mode == 0o600
