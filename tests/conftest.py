"""Shared pytest fixtures.

Tests get an isolated :class:`AppConfig` rooted at a temp directory (its own
``content/``, ``data/``, ``dist/``) while templates and static assets still
resolve to the real package files, so a build in a test is a faithful
end-to-end exercise of the real theme.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AppConfig, Secrets, UserConfig

TEST_CONFIG_YAML = """
site:
  title: "Test Archive"
  description: "A test archive."
  author: "Test Author"
  url: "https://example.test"
  linkedin_url: "https://www.linkedin.com/in/test"

theme:
  posts_per_page: 4
  featured_count: 2
  recent_count: 3

pagination:
  posts_per_page: 4
  archive_per_page: 4

sync:
  provider: sample
  preserve_deleted: true

categories:
  - name: "Agentic AI"
    slug: "agentic-ai"
    priority: 5
    keywords: ["agentic", "ai agent", "mcp"]
  - name: "Software Engineering"
    slug: "software-engineering"
    priority: 20
    keywords: ["architecture", "engineering", "software"]
  - name: "Leadership"
    slug: "leadership"
    priority: 30
    keywords: ["leadership", "management"]
  - name: "General"
    slug: "general"
    priority: 1000
    keywords: []
"""


@pytest.fixture
def test_config(tmp_path: Path) -> AppConfig:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(TEST_CONFIG_YAML, encoding="utf-8")

    (tmp_path / "content" / "posts").mkdir(parents=True)
    (tmp_path / "content" / "profile").mkdir(parents=True)
    (tmp_path / "content" / "profile" / "profile.yaml").write_text(
        "name: Test Author\nheadline: Testing things\nbio: A bio for tests.\n",
        encoding="utf-8",
    )

    user = UserConfig.load(config_path)
    secrets = Secrets(_env_file=None)  # type: ignore[call-arg]
    return AppConfig(user=user, secrets=secrets, root=tmp_path)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
