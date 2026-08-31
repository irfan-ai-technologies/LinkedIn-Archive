# Content providers

Every source of posts implements the same small interface (`app/ingestion/base.py`):

```python
class ContentProvider(Protocol):
    name: str

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]: ...
```

Nothing outside `app/ingestion/` depends on a concrete provider — the sync engine, CLI, and site generator only ever see `ContentProvider` and `RawPost`/`Post`.

## Bundled providers

| Provider | Module | Requires credentials? |
|---|---|---|
| `sample` | `app/ingestion/sample.py` | No — bundled fictional posts, used for demos, development, and CI |
| `import` | `app/ingestion/json_import.py` | No — reads a local JSON file |
| `linkedin_export` | `app/ingestion/linkedin_export.py` | No — reads LinkedIn's own personal data export |
| `linkedin` | `app/ingestion/linkedin.py` + `linkedin_oauth.py` | Yes — see [`linkedin-api.md`](linkedin-api.md) |

## Importing from LinkedIn's own data export

As of this writing, LinkedIn is not accepting new access requests for the `r_member_social`
scope the `linkedin` provider needs — its own Marketing API FAQ calls the permission "closed...
due to resource constraints." Until that changes, the `linkedin_export` provider is the way to
populate a fork from your real post history:

1. On LinkedIn: Settings & Privacy → Data privacy → **Get a copy of your data** → select **Posts**
   (for your posts) and, separately, **Profile** (for the About page — see below). LinkedIn emails
   you a zip within a few minutes to a day.
2. Unzip it. Somewhere inside is `Shares.csv` (your posts) and `Profile.csv` (your profile fields).
3. Run:

   ```bash
   uv run linkedin-archive import-export path/to/unzipped-export/
   ```

This reads `Shares.csv` directly — no conversion step needed. Column names have varied across
LinkedIn's export format revisions, so lookups are case/punctuation-insensitive against a list of
known aliases; if `Shares.csv`'s headers don't match any known alias, the command fails with the
headers it actually found so the aliases in `app/ingestion/linkedin_export.py` can be extended.

A bare repost (no commentary, nothing shared) has nothing to archive and is skipped. A row whose
date can't be parsed is skipped too, rather than failing the whole import.

This is not scraping — it's reading a file LinkedIn generated and handed directly to you.

### Populating the About page from `Profile.csv`

```bash
uv run linkedin-archive import-profile path/to/unzipped-export/Profile.csv
```

This updates `name`, `headline`, `bio`, and `location` in `content/profile/profile.yaml` (which
already drives the About page and home page bio — see `app/storage/profile_store.py`) from the
matching columns in `Profile.csv`. Fields the export has no equivalent for — `avatar` and
`links` (LinkedIn/GitHub/website/email) — are always left as they were; edit those by hand.

## The JSON import format

```json
{
  "posts": [
    {
      "id": "123",
      "published_at": "2026-08-20T10:30:00Z",
      "text": "Post body text. #AgenticAI #MCP",
      "url": "https://www.linkedin.com/posts/you_...",
      "title": "Optional — falls back to the first sentence of text",
      "author": "Optional — falls back to site.author",
      "updated_at": "Optional ISO-8601 timestamp",
      "hashtags": ["Optional", "explicit", "list"],
      "media": [
        {"type": "image", "url": "https://...", "alt_text": "..."}
      ],
      "language": "en"
    }
  ]
}
```

Only `id`, `published_at`, and `text` are required. Hashtags and links are auto-extracted from `text` if not explicitly provided. Run it with:

```bash
uv run linkedin-archive import posts.json
```

Imported posts get IDs prefixed `import-<id>` and are fully independent of any LinkedIn-sourced posts — a later LinkedIn sync will never touch or delete them (see `sync.preserve_deleted` in [`configuration.md`](configuration.md)).

## Writing a new provider

As a worked example, here's what a minimal RSS-feed provider would look like:

```python
# app/ingestion/rss_feed.py
from datetime import datetime
import httpx
from app.models.post import RawPost
from app.ingestion.normalize import extract_hashtags, extract_links


class RssFeedProvider:
    name = "rss"

    def __init__(self, feed_url: str) -> None:
        self.feed_url = feed_url

    def fetch_posts(self, since: datetime | None = None) -> list[RawPost]:
        # 1. Fetch and parse the feed (your own parsing logic here).
        # 2. Map each entry to a RawPost, reusing the shared helpers:
        return [
            RawPost(
                id=f"rss-{entry_id}",
                source=self.name,
                source_id=entry_id,
                author=author,
                published_at=published_at,
                text=body_text,
                hashtags=extract_hashtags(body_text),
                links=extract_links(body_text),
                raw_metadata=raw_entry,
            )
            for entry_id, author, published_at, body_text, raw_entry in ...
        ]
```

Then register it in `app/ingestion/__init__.py`'s `get_provider()` (for `sync`) or wire it up directly wherever it's invoked. No change is needed anywhere in `app/enrichment/`, `app/storage/`, `app/search/`, or `app/site/` — they only ever see `RawPost`/`Post`.

### Guidelines for new providers

- Preserve the original payload in `raw_metadata` so reprocessing never requires calling the source again.
- Extract hashtags/links with `app/ingestion/normalize.py`'s helpers so tagging behaves consistently across providers.
- Never raise on a filter it can't support (e.g. `since`) — filter locally instead, or ignore it.
- Raise `app.ingestion.base.ProviderError` (with a clear, actionable message) for genuine failures; the sync engine already handles one bad post not aborting the whole run.
- Never fetch or process anything requiring stored passwords/scraping — see the [Security policy](../SECURITY.md).
