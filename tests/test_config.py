from pathlib import Path

from app.config import UserConfig, load_config


def test_site_url_trailing_slash_stripped() -> None:
    config = UserConfig.model_validate({"site": {"url": "https://example.com/"}})
    assert config.site.url == "https://example.com"


def test_missing_config_file_uses_defaults(tmp_path: Path) -> None:
    config = UserConfig.load(tmp_path / "does-not-exist.yaml")
    assert config.site.title == "My LinkedIn Archive"


def test_sorted_categories_respects_priority() -> None:
    config = UserConfig.model_validate(
        {
            "categories": [
                {"name": "B", "slug": "b", "priority": 20},
                {"name": "A", "slug": "a", "priority": 5},
            ]
        }
    )
    assert [c.name for c in config.sorted_categories()] == ["A", "B"]


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text('site:\n  title: "Custom Title"\n', encoding="utf-8")
    app_config = load_config(config_path, root=tmp_path)
    assert app_config.user.site.title == "Custom Title"
    assert app_config.posts_dir == tmp_path / "content" / "posts"


def test_templates_and_static_resolve_to_package_root(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("site:\n  title: X\n", encoding="utf-8")
    app_config = load_config(config_path, root=tmp_path)
    assert app_config.templates_dir.exists()
    assert (app_config.templates_dir / "base.html").exists()
    assert app_config.static_dir.exists()
