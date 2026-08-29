import time

import httpx
import pytest
import respx

from app.ingestion.base import ProviderError
from app.ingestion.linkedin import LinkedInProvider
from app.ingestion.linkedin_oauth import TokenSet


def _provider(**kwargs: object) -> LinkedInProvider:
    tokens = TokenSet(access_token="valid-token", expires_at=time.time() + 3600)
    defaults: dict[str, object] = {"client_id": "id", "client_secret": "secret", "tokens": tokens}
    defaults.update(kwargs)
    return LinkedInProvider(**defaults)  # type: ignore[arg-type]


@respx.mock
def test_fetch_posts_normalizes_elements() -> None:
    respx.get("https://api.linkedin.com/v2/userinfo").mock(
        return_value=httpx.Response(200, json={"sub": "abc123"})
    )
    respx.get("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "id": "urn:li:share:111",
                        "author": "urn:li:person:abc123",
                        "commentary": "Loving #AgenticAI systems https://example.com",
                        "createdAt": 1750000000000,
                        "lastModifiedAt": 1750000100000,
                    }
                ],
                "paging": {"total": 1},
            },
        )
    )
    provider = _provider()
    posts = provider.fetch_posts()
    assert len(posts) == 1
    post = posts[0]
    assert post.source == "linkedin"
    assert post.id == "linkedin-111"
    assert "AgenticAI" in post.hashtags
    assert post.source_url is not None


@respx.mock
def test_fetch_posts_paginates() -> None:
    respx.get("https://api.linkedin.com/v2/userinfo").mock(
        return_value=httpx.Response(200, json={"sub": "abc123"})
    )

    def make_page(start: int, total: int, count: int) -> httpx.Response:
        elements = [
            {
                "id": f"urn:li:share:{start + i}",
                "author": "urn:li:person:abc123",
                "commentary": "post text",
                "createdAt": 1750000000000,
            }
            for i in range(count)
        ]
        return httpx.Response(200, json={"elements": elements, "paging": {"total": total}})

    route = respx.get("https://api.linkedin.com/rest/posts")
    route.side_effect = [
        make_page(0, 3, 2),
        make_page(2, 3, 1),
    ]

    posts = _provider().fetch_posts()
    assert len(posts) == 3


@respx.mock
def test_403_raises_helpful_provider_error() -> None:
    respx.get("https://api.linkedin.com/v2/userinfo").mock(
        return_value=httpx.Response(200, json={"sub": "abc123"})
    )
    respx.get("https://api.linkedin.com/rest/posts").mock(return_value=httpx.Response(403))

    with pytest.raises(ProviderError) as exc_info:
        _provider().fetch_posts()
    assert "r_member_social" in str(exc_info.value)


@respx.mock
def test_userinfo_failure_raises_provider_error() -> None:
    respx.get("https://api.linkedin.com/v2/userinfo").mock(return_value=httpx.Response(401))
    with pytest.raises(ProviderError):
        _provider().fetch_posts()


def test_expired_token_without_refresh_raises() -> None:
    tokens = TokenSet(access_token="expired", expires_at=time.time() - 10)
    provider = _provider(tokens=tokens)
    with pytest.raises(ProviderError, match="run `linkedin-archive auth login`"):
        provider.fetch_posts()


@respx.mock
def test_expired_token_is_refreshed_automatically() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(200, json={"access_token": "new-token", "expires_in": 3600})
    )
    respx.get("https://api.linkedin.com/v2/userinfo").mock(
        return_value=httpx.Response(200, json={"sub": "abc123"})
    )
    respx.get("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(200, json={"elements": [], "paging": {"total": 0}})
    )

    refreshed: list[TokenSet] = []
    tokens = TokenSet(access_token="old", expires_at=time.time() - 10, refresh_token="refresh-1")
    provider = _provider(tokens=tokens, on_token_refresh=refreshed.append)
    provider.fetch_posts()

    assert refreshed
    assert refreshed[0].access_token == "new-token"
