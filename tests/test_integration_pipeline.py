"""End-to-end pipeline test.

sample JSON -> normalize -> categorize -> generate Markdown -> build static
site -> verify expected pages exist. No LinkedIn credentials are used or
required anywhere in this test.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import AppConfig
from app.ingestion.json_import import JsonImportProvider
from app.site.generator import build_site
from app.storage.store import PostStore
from app.sync import run_sync
from app.validation import validate_repository


def test_full_pipeline_from_json_import_to_static_site(
    test_config: AppConfig, tmp_path: Path
) -> None:
    import_file = tmp_path / "posts.json"
    import_file.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "id": "1",
                        "published_at": "2026-01-05T09:00:00Z",
                        "author": "Integration Author",
                        "title": "Agentic systems in production",
                        "text": (
                            "Running agentic AI systems in production taught us a lot about "
                            "tool design. #AgenticAI #MCP"
                        ),
                        "url": "https://www.linkedin.com/posts/x-1",
                    },
                    {
                        "id": "2",
                        "published_at": "2026-02-10T09:00:00Z",
                        "author": "Integration Author",
                        "text": "Good software architecture reduces the cost of change. #SoftwareEngineering",
                        "url": "https://www.linkedin.com/posts/x-2",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    # 1. Normalize + categorize + store as Markdown via the sync engine.
    provider = JsonImportProvider(import_file, default_author="Integration Author")
    result = run_sync(provider, test_config)
    assert result.new == 2
    assert result.failed == 0

    store = PostStore(test_config.posts_dir)
    posts = store.load_all()
    assert len(posts) == 2
    assert {p.category for p in posts} == {"Agentic AI", "Software Engineering"}

    # Markdown files exist with YAML front matter on disk.
    md_files = list(test_config.posts_dir.glob("*.md"))
    assert len(md_files) == 2
    assert md_files[0].read_text(encoding="utf-8").startswith("---\n")

    # 2. Re-running sync is idempotent.
    result_again = run_sync(
        JsonImportProvider(import_file, default_author="Integration Author"), test_config
    )
    assert result_again.new == 0
    assert result_again.unchanged == 2

    # 3. Repository validates cleanly.
    report = validate_repository(test_config)
    assert report.ok, report.summary_text()

    # 4. Build the static site and verify the expected output exists.
    dist = build_site(test_config)
    assert (dist / "index.html").exists()
    assert (dist / "posts" / "import-1" / "index.html").exists()
    assert (dist / "posts" / "import-2" / "index.html").exists()
    assert (dist / "categories" / "agentic-ai" / "index.html").exists()
    assert (dist / "tags" / "mcp" / "index.html").exists()
    assert (dist / "search-index.json").exists()
    assert (dist / "feed.xml").exists()
    assert (dist / "sitemap.xml").exists()

    search_data = json.loads((dist / "search-index.json").read_text(encoding="utf-8"))
    assert search_data["count"] == 2

    post_html = (dist / "posts" / "import-1" / "index.html").read_text(encoding="utf-8")
    assert "Agentic systems in production" in post_html
    assert "www.linkedin.com/posts/x-1" in post_html
