# Configuration reference

Everything here lives in `config.yaml` at the repository root — no Python code. Secrets (LinkedIn credentials) are environment variables only; see `.env.example` and [`linkedin-api.md`](linkedin-api.md).

## `site`

| Key | Meaning |
|---|---|
| `title`, `description`, `author` | Used in page titles, meta descriptions, RSS, and JSON-LD. |
| `url` | Public base URL of the deployed site, no trailing slash. Used for canonical URLs, sitemap, RSS. Can be overridden per-environment via the `LINKEDIN_ARCHIVE_SITE_URL` environment variable (useful in CI). |
| `linkedin_url` | Your LinkedIn profile URL, linked from the header/footer/home page. |
| `language` | BCP-47-ish language code, used in `<html lang>` and RSS. |
| `links.github` / `links.website` / `links.email` | Optional footer links. |

## `theme`

| Key | Meaning |
|---|---|
| `default_mode` | `auto` (respect OS preference), `light`, or `dark`. |
| `accent_color` | Hex color used for links, badges, and the theme-color meta tag. |
| `posts_per_page`, `featured_count`, `recent_count` | Home page and archive list sizing. |
| `show_reading_time`, `show_word_count` | Toggle post-meta display. |

## `sync`

| Key | Meaning |
|---|---|
| `enabled` | Set `false` to make `linkedin-archive sync` a no-op (useful for a purely import-driven archive). |
| `provider` | `linkedin` or `sample`. (`import` is always invoked explicitly via `linkedin-archive import <file>`, not through this setting.) |
| `initial_lookback_days` | How far back the first sync should look (providers may ignore this if they can't filter server-side). |
| `preserve_deleted` | `true` (default): posts that disappear from the source stay in your archive. `false`: they're deleted from `content/posts/` on the next sync — but only posts belonging to the source that was just synced (an `import`-sourced post is never removed by a `linkedin` sync, and vice versa). |

## `search`

| Key | Meaning |
|---|---|
| `max_indexed_chars` | Truncates each post's body in the client search index to keep `search-index.json` small on large archives. Excerpts and titles are always included in full. |

## `pagination`

| Key | Meaning |
|---|---|
| `posts_per_page` | Used for the all-posts listing, category pages, and tag pages. |
| `archive_per_page` | Used for year archive pages. |

## Categories

```yaml
categories:
  - name: "Agentic AI"        # display name
    slug: "agentic-ai"        # URL slug, e.g. /categories/agentic-ai/
    description: "..."        # shown on the category page
    priority: 5                # lower number = matched first
    keywords:
      - "agentic"
      - "ai agent"
      - "mcp"
```

**How categorization works** (`app/enrichment/categorizer.py`, `KeywordCategorizer`):

- Categories are evaluated in `priority` order (lowest first). A post's **primary category** is the first category with at least one keyword or hashtag match (case-insensitive substring match against the post body, and exact match against hashtags).
- If nothing matches, the post falls back to `"General"`.
- **Tags** are the union of: every hashtag on the post (slugified — `AgenticAI` → `agentic-ai`, acronyms like `MCP` are kept intact), plus the slug of *every* category whose keywords matched (not just the primary one).
- This is pure keyword matching — no LLM call, no network access, fully deterministic. `Categorizer` (`app/enrichment/categorizer.py`) is a small `Protocol`, so an LLM-based categorizer could be added later as an alternative implementation without changing anything else.

Categories are entirely yours to define — there is no hardcoded category anywhere in the codebase. A post whose `category` (set manually in front matter, or previously computed) doesn't match any configured category still renders fine; `linkedin-archive validate` will just warn about it.

## Profile

`content/profile/profile.yaml` (not `config.yaml`) holds the About-page content:

```yaml
name: "Your Name"
headline: "One-line professional headline"
location: "City, Country"
bio: |
  Multi-paragraph Markdown bio.
avatar: null   # or a path/URL to an image
links:
  linkedin: "..."
  github: "..."
  website: ""
  email: ""
```
