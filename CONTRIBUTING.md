# Contributing to LinkedIn Archive

Thanks for considering a contribution. This project is meant to stay small, readable, and forkable — please keep that in mind for any change.

## Development setup

```bash
git clone https://github.com/<you>/linkedin-archive.git
cd linkedin-archive
uv sync --extra dev
uv run linkedin-archive build
uv run linkedin-archive serve
```

## Before opening a pull request

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

All four must pass. CI runs the same checks on every pull request.

## Guidelines

- **Keep layers separate.** Code under `app/site/`, `app/search/`, `app/enrichment/`, and `app/storage/` must not import anything from `app/ingestion/`. If you're adding a feature that only makes sense for LinkedIn, it almost certainly belongs in `app/ingestion/linkedin.py`, not upstream of it.
- **No LinkedIn scraping, ever.** Any change touching LinkedIn integration must go through the official OAuth API only (see `docs/linkedin-api.md`). PRs that add scraping, browser automation, or credential storage will be closed.
- **No personal configuration in code.** `config.yaml`, `content/`, and environment variables are the only places user-specific values belong. Application code must work for any fork with only those changed.
- **Test new behavior.** New providers, enrichment logic, or site-generation features should ship with tests under `tests/`. Use the bundled `sample` provider or fixtures under `tests/fixtures/` — never real personal data.
- **Deterministic builds.** Anything written into `content/` or `dist/` must be reproducible from the same inputs — no embedded timestamps, random IDs, or dict-ordering dependent output.
- **Small, focused changes.** Prefer several small PRs over one large one.

## Reporting bugs / requesting features

Open a GitHub issue with steps to reproduce (for bugs) or the use case you're trying to solve (for features). Please redact any personal LinkedIn content from logs or screenshots before posting.

## Security issues

Please do not open a public issue for a security vulnerability — see [`SECURITY.md`](SECURITY.md).
