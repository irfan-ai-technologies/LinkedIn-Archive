# Architecture

## Pipeline

```
ContentProvider.fetch_posts()  →  RawPost  →  enrich_post()  →  Post  →  PostStore (Markdown)  →  SiteGenerator  →  dist/
```

1. **Ingestion** (`app/ingestion/`) — a `ContentProvider` fetches posts from a source and normalizes them into `RawPost` (`app/models/post.py`). This is the only layer allowed to know about a specific source's API shape.
2. **Enrichment** (`app/enrichment/`) — `enrich_post()` turns a `RawPost` into a fully-populated `Post`: categorization (`KeywordCategorizer`), word count, reading time, excerpt, and derived title.
3. **Storage** (`app/storage/`) — `PostStore` reads/writes `Post` objects as Markdown files with YAML front matter under `content/posts/`. `RawArchive` separately persists each provider's raw payload under `data/raw/` for future reprocessing.
4. **Sync engine** (`app/sync.py`) — orchestrates 1–3, idempotently: new posts are created, changed posts are updated (preserving the manually-set `featured` flag), unchanged posts are left alone, and posts are never deleted unless `sync.preserve_deleted: false`.
5. **Search** (`app/search/`) — `dump_search_index()` builds a compact JSON index from all posts, written to `dist/search-index.json` and searched entirely client-side (`static/js/search.js`).
6. **Site generation** (`app/site/`) — `SiteGenerator` reads all posts via `PostStore`, renders every page with Jinja2, and writes RSS/sitemap/robots.txt/SEO metadata. It has zero knowledge of LinkedIn, OAuth, or any ingestion provider — it depends only on `Post`.
7. **CLI** (`app/cli.py`) — a thin Typer wrapper around the above: `sync`, `build`, `import`, `serve`, `validate`, `stats`, `auth login`.

## Why this separation matters

The website (steps 5–6) is built and tested entirely against the `sample` provider and JSON fixtures — it never needs LinkedIn access to develop or test against. Swapping or adding a source (a personal blog, GitHub activity, another social platform) means writing one more `ContentProvider`; nothing in `app/site/`, `app/search/`, or `app/enrichment/` changes. See [`providers.md`](providers.md).

## Content vs. code vs. generated output

| Directory | Committed to git? | Who edits it |
|---|---|---|
| `config.yaml` | Yes | Fork owner (site config, categories, theme) |
| `content/posts/*.md`, `content/profile/profile.yaml` | Yes | Sync engine + fork owner |
| `app/`, `static/` | Yes | Application code / theme (rarely touched by a fork owner) |
| `data/raw/` | **No** (gitignored) | Sync engine — a local/CI-ephemeral cache of raw provider payloads, regenerated on every sync |
| `dist/` | **No** (gitignored) | Build output — regenerated on every build, published via the GitHub Pages deploy workflow's artifact, never committed |
| `.secrets/`, `.env` | **No** (gitignored) | OAuth tokens and local secrets |

**Why `dist/` isn't committed:** committing generated HTML doubles the size of every content change in git history and invites merge conflicts on machine-generated files. Instead, `deploy.yml` rebuilds `dist/` fresh on every deploy and hands it directly to GitHub's Pages artifact upload/deploy actions — the build is deterministic, so this costs nothing in practice.

**Why `data/raw/` isn't committed:** it's a raw, provider-specific cache kept purely so categorization/excerpt logic can be re-applied without re-fetching from the source. The durable, human-readable archive is `content/posts/*.md` — that's what's committed and that's what the site is built from.

## Determinism

Given the same `content/` and `config.yaml`, `linkedin-archive build` always produces byte-identical output: no embedded timestamps, no random IDs, sorted/ordered dict serialization in front matter, and a compact deterministically-serialized search index. This is what makes it safe to rebuild on every deploy rather than committing `dist/`.

## The `Post` model

`app/models/post.py` defines two models:

- `RawPost` — what a `ContentProvider` produces. Provider-specific data (the untouched API response) is preserved in `raw_metadata` for future reprocessing.
- `Post` — what everything downstream of enrichment consumes. Adds `category`, `tags`, `featured`, `word_count`, `reading_time_minutes`, `excerpt`.

Neither model contains a LinkedIn-specific field. A JSON-imported post and a LinkedIn-synced post are indistinguishable to the site generator.
