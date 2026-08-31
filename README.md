# LinkedIn Archive

An open-source, self-hosted personal website that turns your LinkedIn posts into a beautiful, searchable, categorized, static archive — fully under your control, deployable to GitHub Pages for free.

```
LinkedIn → nightly sync → normalized content → categorization → static site → your domain
```

No ongoing server. No database. No runtime dependency on LinkedIn for visitors. Just Markdown, a static site generator, and GitHub Actions.

---

## What is LinkedIn Archive?

LinkedIn's own platform is a poor place to revisit your own writing: no real search, no categories, no RSS, and everything is one more algorithmic feed away from being buried. LinkedIn Archive fixes that by mirroring your posts into a repository you own, then publishing them as a fast, accessible, SEO-friendly personal site.

It's built to be **forked**, not just run. Every fork owner configures their own site through one YAML file and their own GitHub secrets — no Python knowledge required for day-to-day use.

## Features

- **Nightly sync** from LinkedIn via the official OAuth API (or a local JSON import, or bundled sample data — no LinkedIn access required to get started)
- **Automatic categorization** from a fully configurable keyword/hashtag ruleset
- **Client-side full-text search** — no server, works on category/tag/year filters, ranked by relevance or date
- Home, About, Posts archive, individual post pages, Categories, Tags, Year/Month archive
- **RSS/Atom feed, sitemap.xml, robots.txt, OpenGraph, Twitter cards, JSON-LD Article schema**
- Responsive, accessible, dark/light mode theme with no JS framework
- **Idempotent sync** — safe to run repeatedly, never creates duplicates, never silently deletes history
- Deterministic builds — identical content and config always produce byte-identical output
- Deployable to GitHub Pages (or any static host) with zero servers to maintain

## Architecture

```
LinkedIn API ────────────┐
LinkedIn data export ────┤
JSON import ─────────────┼──▶ ContentProvider ──▶ RawPost ──▶ enrichment ──▶ Post ──▶ content/posts/*.md
Sample data ─────────────┘    (ingestion)                     (categorize,            (Markdown + YAML
                                                              word count,             front matter)
                                                              excerpt)                                    │
                                                                                                          ▼
                                                                                                static site generator
                                                                                               (Jinja2 + search index)
                                                                                                          │
                                                                                                          ▼
                                                                                                          dist/
                                                                                                          │
                                                                                                          ▼
                                                                                               GitHub Pages / any host
```

Each layer only depends on the one below it through a narrow interface:

| Layer | Responsibility | Knows about LinkedIn? |
|---|---|---|
| `app/ingestion/` | Fetch raw posts from a source, normalize into `RawPost` | Only `linkedin.py` / `linkedin_oauth.py` / `linkedin_export.py` / `linkedin_profile_import.py` |
| `app/enrichment/` | Categorize, tag, compute word count/reading time/excerpt | No |
| `app/storage/` | Read/write posts as Markdown + YAML front matter | No |
| `app/search/` | Build the compact client-side search index | No |
| `app/site/` | Render the static site (Jinja2, RSS, sitemap, SEO) | No |
| `app/cli.py` | The `linkedin-archive` command line | No |

The site generator, search index, and templates depend only on the provider-independent `Post` model (`app/models/post.py`). Adding a new source later (a personal blog, GitHub activity, X/Twitter, Medium) means writing one more `ContentProvider` — nothing downstream changes. See [`docs/providers.md`](docs/providers.md).

## Quick start

This is the fastest path to seeing it work, using the bundled fictional sample data — **no LinkedIn credentials needed**:

```bash
git clone https://github.com/<you>/linkedin-archive.git
cd linkedin-archive
uv sync
uv run linkedin-archive build
uv run linkedin-archive serve
```

Open the printed URL. You now have a working archive built from fictional sample posts. From here:

1. Edit `config.yaml` — your name, title, description, LinkedIn URL, categories.
2. Edit `content/profile/profile.yaml` — your bio.
3. Either:
   - **Import your real posts**: export/collect them into the [JSON import format](#importing-existing-posts) and run `uv run linkedin-archive import your-posts.json`, or
   - **Connect LinkedIn's API**: see [LinkedIn API setup](#linkedin-api-setup) below.
4. Push to GitHub, enable Pages, and let the nightly workflow keep it in sync. See [GitHub Actions](#github-actions) and [GitHub Pages deployment](#github-pages-deployment).

**For the full step-by-step guide to set this up for your own profile and your own domain, see [`docs/setup-guide.html`](docs/setup-guide.html).**

## Configuration

Everything a fork owner needs to change lives in **`config.yaml`** (site metadata, theme, categories, pagination) and **environment variables / GitHub Secrets** (credentials only — see `.env.example`). Application code in `app/` should never need to change for day-to-day use.

```yaml
site:
  title: "My LinkedIn Archive"
  url: "https://example.github.io/linkedin-archive"   # or your own domain
  linkedin_url: "https://www.linkedin.com/in/example"

categories:
  - name: "Agentic AI"
    slug: "agentic-ai"
    priority: 5
    keywords: ["agentic", "ai agent", "mcp"]
```

Full reference: [`docs/configuration.md`](docs/configuration.md).

## LinkedIn API setup

Reading a member's own posts requires LinkedIn's **restricted member-social-read permissions** (e.g. `r_member_social`), which require LinkedIn's app review/approval — this is not optional and cannot be bypassed. As of this writing, LinkedIn is not accepting new access requests for this permission at all. **This project never scrapes LinkedIn, never automates a browser, and never stores your LinkedIn password.** It uses LinkedIn's official OAuth 2.0 authorization code flow only.

Until your app is approved (or in place of it, since approval isn't currently obtainable), use the **sample** provider (default), the **linkedin_export** provider (reads LinkedIn's own "Download my data" export — see below), or the **import** provider — all three are fully functional and require no LinkedIn API access.

Full walkthrough, required scopes, and troubleshooting: [`docs/linkedin-api.md`](docs/linkedin-api.md).

Quick version:

```bash
cp .env.example .env
# Fill in LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET from your LinkedIn app
uv run linkedin-archive auth login   # opens a browser, completes OAuth locally
uv run linkedin-archive sync --provider linkedin
```

## Local development

```bash
uv sync                          # install dependencies
uv run linkedin-archive build    # generate dist/ from content/
uv run linkedin-archive serve    # build + serve dist/ locally
uv run linkedin-archive validate # check content and config for problems
uv run linkedin-archive stats    # archive statistics
uv run pytest                    # run the test suite
uv run ruff check .              # lint
uv run ruff format --check .     # formatting
uv run mypy .                    # type-check
```

## Importing existing posts

No LinkedIn API access? Two ways in, no API needed for either:

**From LinkedIn's own data export** — Settings & Privacy → Data privacy → **Get a copy of your data** → check **Posts** (and, separately, **Profile** if you also want the About page filled in — see below). LinkedIn emails a zip; unzip it, then:

```bash
uv run linkedin-archive import-export path/to/unzipped-export/
```

This reads `Shares.csv` directly. See [`docs/providers.md`](docs/providers.md) for details and troubleshooting.

**From a hand-written JSON file:**

```bash
uv run linkedin-archive import posts.json
```

```json
{
  "posts": [
    {
      "id": "123",
      "published_at": "2026-08-20T10:30:00Z",
      "text": "Post body text. #AgenticAI #MCP",
      "url": "https://www.linkedin.com/posts/you_...",
      "title": "Optional title"
    }
  ]
}
```

Either way, imported posts flow through the exact same normalization, categorization, and storage pipeline as the LinkedIn provider — there is no second-class path. See [`docs/providers.md`](docs/providers.md) for the full schema.

## Populating the About page from your LinkedIn profile

If you requested **Profile** in your LinkedIn data export above, `Profile.csv` sits alongside `Shares.csv` in the same unzipped folder:

```bash
uv run linkedin-archive import-profile path/to/unzipped-export/Profile.csv
```

This fills in `name`, `headline`, `bio`, and `location` in `content/profile/profile.yaml` — the file that drives both the About page and the home page bio. It never touches `avatar` or `links` (LinkedIn/GitHub/website/email), since the export has no equivalent data for those; edit them by hand in `content/profile/profile.yaml`.

## GitHub Actions

Two workflows, one job each:

- **`.github/workflows/sync.yml`** — nightly (`workflow_dispatch` also supported), fetches new posts and commits changes to `content/`.
- **`.github/workflows/deploy.yml`** — on push to `content/`, `static/`, `app/site/`, or `config.yaml`, builds the site and publishes it to GitHub Pages via the Pages deployment API (no `dist/` is ever committed to git).

Both need nothing but the repository secrets described in [LinkedIn API setup](#linkedin-api-setup) — or no secrets at all if you're using sample/import content.

## GitHub Pages deployment

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Push to `main` (or run the *Deploy site* workflow manually).
3. Your site is live at `https://<you>.github.io/<repo>/`.

### Custom domains

1. Add a `CNAME` file to `static/` containing your domain (it gets copied into `dist/` on every build), or set it in the repo's Pages settings.
2. Point your domain's DNS at GitHub Pages (an `A`/`AAAA` record set, or a `CNAME` record for a subdomain).
3. Update `site.url` in `config.yaml` to your domain.

Full step-by-step instructions (registrar screenshots-in-words, DNS record values, HTTPS): [`docs/setup-guide.html`](docs/setup-guide.html) and [`docs/deployment.md`](docs/deployment.md).

## Categorization

Fully rule-based, fully configurable, no LLM required. Each post gets one primary category (highest-priority keyword/hashtag match) and any number of tags (every hashtag, plus every category whose keywords matched). Edit the `categories:` list in `config.yaml` — no code changes needed. See [`docs/configuration.md`](docs/configuration.md#categories).

## Search

Fully client-side: a compact JSON index (`search-index.json`) is generated at build time and searched in the browser with `static/js/search.js` — no backend, no visitor query ever leaves the browser. Supports keyword search plus category/tag/year filters and relevance/date sorting. Press `/` anywhere on the site to jump to search.

## Customizing the theme

Templates live in `app/site/templates/` (Jinja2), styles in `static/css/style.css`, behavior in `static/js/`. No build step — edit and rebuild. See [`docs/customization.md`](docs/customization.md).

## Adding a new content provider

Implement the `ContentProvider` protocol (`app/ingestion/base.py`): one method, `fetch_posts(since=None) -> list[RawPost]`. See [`docs/providers.md`](docs/providers.md) for a worked example.

## Troubleshooting

| Problem | Likely cause |
|---|---|
| `linkedin-archive sync` fails with `403 Forbidden` | Your LinkedIn app hasn't been approved for member-social-read permissions yet. Use `sample` or `import` in the meantime. |
| `auth login` never redirects back | Check `LINKEDIN_REDIRECT_URI` matches exactly what's registered on your LinkedIn app, port included. |
| Build succeeds but search shows no results | Check the browser console for a fetch error on `/search-index.json` — usually a base-path issue if the site is served from a subdirectory. |
| GitHub Pages shows a 404 | Confirm Pages source is set to "GitHub Actions" and the `deploy.yml` run succeeded. |
| Sync workflow can't push | Confirm the workflow has `permissions: contents: write` (already set) and branch protection allows the `github-actions[bot]` account to push. |

More in [`docs/deployment.md`](docs/deployment.md) and [`docs/linkedin-api.md`](docs/linkedin-api.md).

## Security

- No LinkedIn credentials are ever committed. OAuth tokens are stored outside the repo (`.secrets/`, gitignored) or in GitHub Secrets.
- Post content is treated as untrusted input: rendered Markdown is sanitized (`app/site/render.py`) to strip scripts, event handlers, and `javascript:` URLs before it reaches the page.
- No scraping, no headless browser automation, no stored LinkedIn password — OAuth 2.0 only.
- See [`SECURITY.md`](SECURITY.md) (or open an issue) to report a vulnerability.

## FAQ

**Do I need to know Python?** No — fork, edit `config.yaml`, set secrets, enable Pages.

**Do I need LinkedIn API access to start?** No — the sample provider works out of the box, and JSON import works for real content with zero API access.

**Will this ever auto-delete my posts?** No. Posts that disappear from the source are kept by default (`sync.preserve_deleted: true` in `config.yaml`).

**Can I self-host instead of GitHub Pages?** Yes — `dist/` is a plain static site; deploy it anywhere (Netlify, Cloudflare Pages, S3, nginx).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
