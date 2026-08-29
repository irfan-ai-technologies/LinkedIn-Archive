"""The ``linkedin-archive`` command-line interface."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import typer

from app.config import AppConfig, load_config
from app.ingestion import ProviderError, get_provider, import_provider
from app.site.devserver import serve_directory
from app.site.generator import build_site
from app.stats import compute_stats
from app.storage.store import PostStore
from app.sync import run_sync
from app.validation import validate_repository

app = typer.Typer(
    name="linkedin-archive",
    help="Turn your LinkedIn posts into a searchable, categorized, static personal website.",
    add_completion=False,
    no_args_is_help=True,
)

auth_app = typer.Typer(help="Manage LinkedIn OAuth credentials.")
app.add_typer(auth_app, name="auth")

_config_option = typer.Option(
    None, "--config", "-c", help="Path to config.yaml (defaults to repo root)."
)


def _load(config_path: Path | None) -> AppConfig:
    return load_config(config_path) if config_path else load_config()


@app.command()
def sync(
    provider_name: str = typer.Option(
        None, "--provider", "-p", help="Override sync.provider from config.yaml (linkedin|sample)."
    ),
    config_path: Path | None = _config_option,
) -> None:
    """Fetch posts from the configured provider and rebuild the site."""
    config = _load(config_path)
    name = provider_name or config.user.sync.provider

    try:
        provider = get_provider(name, config)
    except ProviderError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    result = run_sync(provider, config)
    typer.echo(result.summary_text())

    if result.failed and result.fetched == 0:
        raise typer.Exit(code=1)

    build_site(config)
    typer.echo("\nStatic site generated successfully.")


@app.command(name="import")
def import_command(
    file: Path = typer.Argument(
        ..., help="Path to a JSON file in the LinkedIn Archive import format."
    ),
    author: str = typer.Option(None, "--author", help="Default author for posts missing one."),
    config_path: Path | None = _config_option,
) -> None:
    """Import posts from a local JSON file (no LinkedIn credentials required)."""
    config = _load(config_path)
    provider = import_provider(file, default_author=author or config.user.site.author)

    try:
        result = run_sync(provider, config)
    except ProviderError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result.summary_text())
    if result.failed and result.fetched == 0:
        raise typer.Exit(code=1)

    build_site(config)
    typer.echo("\nStatic site generated successfully.")


@app.command()
def build(config_path: Path | None = _config_option) -> None:
    """Generate the static site from content/ into dist/."""
    config = _load(config_path)
    dist = build_site(config)
    post_count = len(PostStore(config.posts_dir).load_all())
    typer.echo(f"Built {post_count} posts into {dist}")


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
    no_build: bool = typer.Option(
        False, "--no-build", help="Serve the existing dist/ without rebuilding."
    ),
    config_path: Path | None = _config_option,
) -> None:
    """Build (unless --no-build) and serve the site locally."""
    config = _load(config_path)
    if not no_build:
        build_site(config)
    serve_directory(config.dist_dir, host=host, port=port)


@app.command()
def validate(config_path: Path | None = _config_option) -> None:
    """Check content and configuration for problems."""
    config = _load(config_path)
    report = validate_repository(config)
    typer.echo(report.summary_text())
    if not report.ok:
        raise typer.Exit(code=1)


@app.command()
def stats(config_path: Path | None = _config_option) -> None:
    """Show archive statistics."""
    config = _load(config_path)
    posts = PostStore(config.posts_dir).load_all()
    typer.echo(compute_stats(posts).summary_text())


@auth_app.command("login")
def auth_login(config_path: Path | None = _config_option) -> None:
    """Interactively authorize LinkedIn Archive to read your own posts via OAuth."""
    from app.ingestion.linkedin_auth_server import await_oauth_callback
    from app.ingestion.linkedin_oauth import (
        LinkedInAuthError,
        TokenStore,
        build_authorization_url,
        exchange_code_for_token,
    )

    config = _load(config_path)
    secrets = config.secrets
    if not secrets.linkedin_client_id or not secrets.linkedin_client_secret:
        typer.echo(
            "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set (see .env.example).",
            err=True,
        )
        raise typer.Exit(code=1)

    url, state = build_authorization_url(
        client_id=secrets.linkedin_client_id, redirect_uri=secrets.linkedin_redirect_uri
    )
    typer.echo(f"Opening your browser to authorize LinkedIn Archive:\n{url}\n")
    webbrowser.open(url)

    result = await_oauth_callback(secrets.linkedin_redirect_uri)
    if result.error or not result.code:
        typer.echo(f"Authorization failed: {result.error or 'no code received'}", err=True)
        raise typer.Exit(code=1)
    if result.state != state:
        typer.echo("Authorization failed: state mismatch (possible CSRF).", err=True)
        raise typer.Exit(code=1)

    try:
        tokens = exchange_code_for_token(
            client_id=secrets.linkedin_client_id,
            client_secret=secrets.linkedin_client_secret,
            redirect_uri=secrets.linkedin_redirect_uri,
            code=result.code,
        )
    except LinkedInAuthError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    TokenStore(secrets.linkedin_token_store).save(tokens)
    typer.echo(
        f"Saved LinkedIn credentials to {secrets.linkedin_token_store}. You can now run `linkedin-archive sync`."
    )


def main() -> None:
    try:
        app()
    except ProviderError as exc:  # pragma: no cover - defensive top-level guard
        typer.echo(str(exc), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
