"""Application configuration.

Two distinct sources are combined here, deliberately kept separate:

* ``config.yaml`` (or a path override) — USER CONFIGURATION. Site metadata,
  theme, categories, pagination. No secrets. Safe to commit and edit without
  touching Python code.
* Environment variables (optionally loaded from a local ``.env``) — SECRETS
  and per-environment overrides. Never committed.

Nothing else in the application should read ``config.yaml`` or environment
variables directly; everything goes through :class:`AppConfig`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class SiteLinks(BaseModel):
    github: str = ""
    website: str = ""
    email: str = ""


class SiteConfig(BaseModel):
    title: str = "My LinkedIn Archive"
    description: str = ""
    author: str = "Anonymous"
    url: str = "http://localhost:8000"
    linkedin_url: str = ""
    language: str = "en"
    timezone: str = "UTC"
    links: SiteLinks = Field(default_factory=SiteLinks)

    @field_validator("url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class ThemeConfig(BaseModel):
    default_mode: str = "auto"
    accent_color: str = "#0a66c2"
    posts_per_page: int = 12
    featured_count: int = 3
    recent_count: int = 6
    show_reading_time: bool = True
    show_word_count: bool = False


class SyncConfig(BaseModel):
    enabled: bool = True
    provider: str = "sample"
    initial_lookback_days: int = 365
    preserve_deleted: bool = True


class SearchConfig(BaseModel):
    max_indexed_chars: int = 4000


class PaginationConfig(BaseModel):
    posts_per_page: int = 12
    archive_per_page: int = 50


class CategoryConfig(BaseModel):
    name: str
    slug: str
    description: str = ""
    priority: int = 100
    keywords: list[str] = Field(default_factory=list)


class UserConfig(BaseModel):
    """The fully parsed contents of ``config.yaml``."""

    site: SiteConfig = Field(default_factory=SiteConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    categories: list[CategoryConfig] = Field(default_factory=list)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> UserConfig:
        path = Path(path)
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def sorted_categories(self) -> list[CategoryConfig]:
        return sorted(self.categories, key=lambda c: c.priority)


class Secrets(BaseSettings):
    """Environment-derived secrets and overrides. Never logged or persisted."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8765/callback"
    linkedin_token_store: str = ".secrets/linkedin_token.json"
    linkedin_archive_site_url: str = ""
    log_level: str = "INFO"


class AppConfig(BaseModel):
    """Combined, ready-to-use application configuration."""

    user: UserConfig
    secrets: Secrets
    root: Path = PROJECT_ROOT

    model_config = {"arbitrary_types_allowed": True}

    @property
    def content_dir(self) -> Path:
        return self.root / "content"

    @property
    def posts_dir(self) -> Path:
        return self.content_dir / "posts"

    @property
    def profile_path(self) -> Path:
        return self.content_dir / "profile" / "profile.yaml"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def dist_dir(self) -> Path:
        return self.root / "dist"

    @property
    def static_dir(self) -> Path:
        # Templates and static assets ship with the application package
        # itself (not with a fork's content root), so they always resolve
        # relative to PROJECT_ROOT — even when `root` is pointed at an
        # isolated content directory, e.g. in tests.
        return PROJECT_ROOT / "static"

    @property
    def templates_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "site" / "templates"

    @property
    def site_url(self) -> str:
        return (self.secrets.linkedin_archive_site_url or self.user.site.url).rstrip("/")


def load_config(
    config_path: Path | str = DEFAULT_CONFIG_PATH, root: Path | None = None
) -> AppConfig:
    """Load the combined application configuration.

    ``content/``, ``data/``, and ``dist/`` are resolved relative to
    ``config_path``'s directory by default (they are expected to be
    siblings of ``config.yaml``), not the installed package location —
    pointing ``--config`` at a different repo/checkout works as expected.
    Pass ``root`` explicitly to override this.
    """
    config_path = Path(config_path)
    user = UserConfig.load(config_path)
    secrets = Secrets()
    return AppConfig(user=user, secrets=secrets, root=root or config_path.parent)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cached accessor for the default configuration. Prefer explicit loading in tests."""
    return load_config()
