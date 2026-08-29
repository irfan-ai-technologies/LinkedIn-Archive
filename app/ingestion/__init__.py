"""Content providers: LinkedIn ingestion is one adapter among several.

The application core only ever depends on :class:`ContentProvider`. Use
:func:`get_provider` to construct a named provider from configuration
rather than importing a concrete provider class directly.
"""

from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.ingestion.base import ContentProvider, ProviderError
from app.ingestion.json_import import JsonImportProvider
from app.ingestion.sample import SampleProvider

__all__ = [
    "ContentProvider",
    "JsonImportProvider",
    "ProviderError",
    "SampleProvider",
    "get_provider",
]


def get_provider(name: str, config: AppConfig) -> ContentProvider:
    """Construct a provider by name for use with ``sync``."""
    if name == "sample":
        return SampleProvider()
    if name == "linkedin":
        from app.ingestion.linkedin import LinkedInProvider
        from app.ingestion.linkedin_oauth import TokenStore

        store = TokenStore(config.secrets.linkedin_token_store)
        tokens = store.load()
        if tokens is None:
            raise ProviderError(
                "linkedin",
                "no stored credentials found; run `linkedin-archive auth login` first",
            )
        provider = LinkedInProvider(
            client_id=config.secrets.linkedin_client_id,
            client_secret=config.secrets.linkedin_client_secret,
            tokens=tokens,
            on_token_refresh=store.save,
        )
        return provider
    if name == "import":
        raise ProviderError(
            "import",
            "the import provider requires a file path; use `linkedin-archive import <file>`",
        )
    raise ProviderError(name, f"unknown provider: {name!r}")


def import_provider(path: Path | str, default_author: str) -> JsonImportProvider:
    return JsonImportProvider(path, default_author=default_author)
