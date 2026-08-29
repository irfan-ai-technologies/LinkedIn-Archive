from pathlib import Path

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
site:
  title: "CLI Test Archive"
  url: "https://example.test"
sync:
  provider: sample
""",
        encoding="utf-8",
    )
    (tmp_path / "content" / "posts").mkdir(parents=True)
    (tmp_path / "content" / "profile").mkdir(parents=True)
    (tmp_path / "content" / "profile" / "profile.yaml").write_text(
        "name: CLI Test\n", encoding="utf-8"
    )
    return config_path


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "sync" in result.output
    assert "build" in result.output
    assert "validate" in result.output


def test_sync_with_sample_provider_then_build(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    config_path = _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["sync", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "Fetched:" in result.output
    assert (tmp_path / "dist" / "index.html").exists()


def test_import_command(tmp_path: Path, fixtures_dir: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(
        app,
        ["import", str(fixtures_dir / "import_posts.json"), "--config", str(config_path)],
    )
    assert result.exit_code == 0, result.output
    assert "New:" in result.output
    assert (tmp_path / "dist" / "index.html").exists()


def test_build_command_reports_post_count(tmp_path: Path, fixtures_dir: Path) -> None:
    config_path = _write_config(tmp_path)
    runner.invoke(
        app, ["import", str(fixtures_dir / "import_posts.json"), "--config", str(config_path)]
    )
    result = runner.invoke(app, ["build", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Built 3 posts" in result.output


def test_validate_command_clean_repo(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["validate", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "No issues found" in result.output


def test_stats_command(tmp_path: Path, fixtures_dir: Path) -> None:
    config_path = _write_config(tmp_path)
    runner.invoke(
        app, ["import", str(fixtures_dir / "import_posts.json"), "--config", str(config_path)]
    )
    result = runner.invoke(app, ["stats", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "Total posts: 3" in result.output


def test_import_missing_file_returns_nonzero(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["import", "does-not-exist.json", "--config", str(config_path)])
    assert result.exit_code != 0


def test_auth_login_requires_credentials(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["auth", "login", "--config", str(config_path)])
    assert result.exit_code != 0
    assert "LINKEDIN_CLIENT_ID" in result.output
