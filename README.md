# LinkedIn Archive

An open-source, self-hosted personal website that turns your LinkedIn posts into a beautiful, searchable, categorized, static archive — fully under your control, deployable to GitHub Pages for free.

```
LinkedIn data export → import-export → normalized content → categorization → static site → your domain
```

No ongoing server. No database. No runtime dependency on LinkedIn for visitors. Just Markdown, a static site generator, and GitHub Actions.

> **LinkedIn API access is not currently available for new forks.** Reading a member's own posts
> requires LinkedIn's `r_member_social` permission, and LinkedIn's own Marketing API FAQ describes
> it as "closed... [not] accepting access requests... due to resource constraints" — not a review
> queue, a dead end for any new application. This isn't a limitation of this project; there is no
> workaround, and this project will never scrape LinkedIn or automate a browser as one. **Use your
> own [LinkedIn data export](#importing-existing-posts) instead** — it requires no approval from
> anyone, gets you the same real posts, and is the path this README leads with below. See
> [LinkedIn API setup](#linkedin-api-setup) for the full explanation.

---

## What is LinkedIn Archive?

LinkedIn's own platform is a poor place to revisit your own writing: no real search, no categories, no RSS, and everything is one more algorithmic feed away from being buried. LinkedIn Archive fixes that by mirroring your posts into a repository you own, then publishing them as a fast, accessible, SEO-friendly personal site.

It's built to be **forked**, not just run. Every fork owner configures their own site through one YAML file and their own GitHub secrets — no Python knowledge required for day-to-day use.

## Features

- **Import your real posts** from your own LinkedIn data export or a JSON file — no LinkedIn API access required, since LinkedIn currently isn't granting any (bundled sample data is also included, for trying the site before importing anything)
- **Nightly sync** from LinkedIn via the official OAuth API, for the rare fork where that access exists or is reopened in the future
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
2. Edit `content/profile/profile.yaml` — your bio (or skip to step 3 and let `import-profile` fill it in for you).
3. Get your real posts in — [request a LinkedIn data export](#importing-existing-posts) and run `uv run linkedin-archive import-export path/to/export/`. (The LinkedIn API is documented too, but LinkedIn isn't currently granting new access to it — see [LinkedIn API setup](#linkedin-api-setup) for why.)
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

## Local development and testing

**Preview the site with whatever content is currently in `content/posts/`** (sample data on a fresh clone, or your imported posts after the step above):

```bash
uv sync                          # install dependencies (once, or after pulling dependency changes)
uv run linkedin-archive build    # generate dist/ from content/ + config.yaml
uv run linkedin-archive serve    # build + serve dist/ locally, prints the URL (typically http://127.0.0.1:8000/)
```

Open the printed URL in a browser and click around — home page, an individual post, `/search/`, `/about/`, dark/light toggle. `serve` rebuilds are not automatic; re-run it (or just `build` again, if `serve` is still running in another terminal — it serves whatever's currently in `dist/`) after changing `content/`, `config.yaml`, or anything under `app/site/`.

**Before trusting or pushing any change**, whether it's new content or a code change:

```bash
uv run linkedin-archive validate # checks content and config for problems: malformed posts, duplicate ids, unknown categories, broken internal links
```

**If you changed application code** under `app/` (as opposed to just content or config), also run the same checks CI runs:

```bash
uv run pytest                    # run the test suite
uv run ruff check .              # lint
uv run ruff format --check .     # formatting
uv run mypy .                    # type-check
```

`uv run linkedin-archive stats` prints a quick summary (post count, categories, date range) if you just want a sanity check that an import did what you expected without opening a browser.

## Importing existing posts

This is the primary way to populate a fork with real content — see [LinkedIn API setup](#linkedin-api-setup) below for why the `linkedin` provider isn't a realistic option right now. Two ways in, neither needs any LinkedIn API access.

### From LinkedIn's own data export (recommended)

**Step 1 — request the export, on linkedin.com (not this repo):**

1. Click your profile photo → **Settings & Privacy**.
2. **Data privacy** (left sidebar) → **Get a copy of your data**.
3. Select **"Want something in particular? Select the data files you're most interested in."**
4. Check **Posts** (your post history). Also check **Profile** if you want [the About page filled in automatically](#populating-the-about-page-from-your-linkedin-profile) too — it costs nothing extra to request both at once.
5. Click **Request archive**. LinkedIn emails you a download link — usually within a few minutes, occasionally up to a day.
6. Click the link in that email and download the `.zip` file (e.g. `Basic_LinkedInDataExport_MM-DD-YYYY.zip` or `Complete_LinkedInDataExport_MM-DD-YYYY.zip`).
7. Unzip it. On macOS/most browsers this happens automatically; otherwise `unzip Basic_LinkedInDataExport_*.zip -d linkedin-export`. Note the folder path — you'll pass it to the CLI next.

**Step 2 — import it, from your cloned fork:**

```bash
uv run linkedin-archive import-export path/to/unzipped-export/
```

This finds and reads your posts CSV directly — named `Shares.csv` in some export variants, `Shares_<a long member id number>.csv` in others; the command locates either. It's safe to re-run any time you request a fresh export: posts are matched by their LinkedIn id, so re-importing never creates duplicates, and a post that no longer appears in a newer export is left alone rather than deleted (`sync.preserve_deleted` in `config.yaml`). See [`docs/providers.md`](docs/providers.md) for details and troubleshooting (e.g. what happens if the CSV's columns don't match what's expected).

### From a hand-written JSON file

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

If you requested **Profile** in your LinkedIn data export above, `Profile.csv` sits alongside your posts CSV in the same unzipped folder:

```bash
uv run linkedin-archive import-profile path/to/unzipped-export/Profile.csv
```

This fills in `name`, `headline`, `bio`, and `location` in `content/profile/profile.yaml` — the file that drives both the About page and the home page bio. It never touches `avatar` or `links` (LinkedIn/GitHub/website/email), since the export has no equivalent data for those; edit them by hand in `content/profile/profile.yaml`. Also double-check the imported `name` — LinkedIn's First/Last Name fields don't always match the capitalization or order you'd actually want displayed.

## LinkedIn API setup

> **Reference only — not currently usable for a new fork.** Reading a member's own posts requires
> LinkedIn's `r_member_social` scope, and LinkedIn's own Marketing API FAQ describes that
> permission as "closed... [not] accepting access requests... due to resource constraints." Not a
> queue you can wait out — closed to new applicants, full stop, as of this writing.

Reading a member's own posts requires LinkedIn's **restricted member-social-read permissions** (e.g. `r_member_social`), which require LinkedIn's app review/approval — this is not optional and cannot be bypassed. **This project never scrapes LinkedIn, never automates a browser, and never stores your LinkedIn password.** It uses LinkedIn's official OAuth 2.0 authorization code flow only.

This section is kept for reference in case LinkedIn reopens the permission. For posts today, use the **linkedin_export** provider (reads LinkedIn's own "Download my data" export — see [Importing existing posts](#importing-existing-posts) above) or the **import** provider — both are fully functional and require no LinkedIn API access.

Full walkthrough, required scopes, and troubleshooting: [`docs/linkedin-api.md`](docs/linkedin-api.md).

Quick version:

```bash
cp .env.example .env
# Fill in LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET from your LinkedIn app
uv run linkedin-archive auth login   # opens a browser, completes OAuth locally
uv run linkedin-archive sync --provider linkedin
```

## GitHub Actions

Two workflows, one job each:

- **`.github/workflows/sync.yml`** — nightly (`workflow_dispatch` also supported), fetches new posts and commits changes to `content/`. Only does anything useful if `sync.provider: linkedin` *and* you have working LinkedIn API access — neither is the default, since that access [currently isn't obtainable](#linkedin-api-setup) for a new fork. Most forks can ignore this workflow entirely and just re-run `import-export`/`import` locally + push when they have new posts.
- **`.github/workflows/deploy.yml`** — on push to `content/`, `static/`, `app/site/`, or `config.yaml`, builds the site and publishes it to GitHub Pages via the Pages deployment API (no `dist/` is ever committed to git).

`deploy.yml` needs no secrets at all. `sync.yml` needs the repository secrets described in [LinkedIn API setup](#linkedin-api-setup) only if `sync.provider: linkedin` — which, per that section, isn't currently a realistic setting for a new fork. For `linkedin_export`/`import` content, re-run the relevant `import-*` command locally and push; there's nothing for `sync.yml` to do.

## GitHub Pages deployment

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Push to `main` (or run the *Deploy site* workflow manually).
3. Your site is live at `https://<you>.github.io/<repo>/`.

### Custom domains

**Step 1 — tell GitHub the domain, in your fork's repo settings (not your DNS provider yet):**

Repo **Settings → Pages → Custom domain**, enter `your-domain.com` or `archive.your-domain.com`, click **Save**. This is a repository setting that applies to every future deploy automatically — no `CNAME` file needed anywhere in the repo (`deploy.yml` publishes via `actions/deploy-pages`, which ignores one even if present).

**Step 2 — add the DNS record, at your domain registrar/DNS provider (Namecheap, GoDaddy, Cloudflare, Google Domains/Squarespace, etc.), not GitHub:**

| If using | Record type | Host / Name | Value |
|---|---|---|---|
| Subdomain (`archive.your-domain.com`) | `CNAME` | `archive` | `<your-github-username>.github.io` |
| Apex domain (`your-domain.com`) | `A` (add all four) | `@` | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` |
| Apex domain, IPv6 (optional) | `AAAA` (add all four) | `@` | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |

The `CNAME` target is always `<username>.github.io` — GitHub routes by the custom domain registered in Step 1, not by which repo that hostname happens to name, so this is correct even if you also separately own a `<username>.github.io` repo. DNS propagation is typically minutes, occasionally a few hours.

**Step 3 — update the site config, back in your cloned fork:**

```bash
# config.yaml
site:
  url: "https://your-domain.com"   # or https://archive.your-domain.com
```

Commit and push — this triggers *Deploy site* automatically and republishes with the corrected canonical URLs, sitemap, and RSS feed.

**Step 4 — verify it's actually live:**

```bash
dig +short CNAME archive.your-domain.com        # should print <your-github-username>.github.io.
curl -sI https://your-domain.com/ | head -1      # should print "HTTP/2 200"
```

Also check repo **Settings → Pages** in the browser: once GitHub verifies the DNS record it issues an HTTPS certificate automatically (can take a few minutes to a few hours after DNS is correct) — revisit that page and check **Enforce HTTPS** once it's no longer greyed out. Until DNS resolves, `dig` prints nothing and `curl` will fail to connect or time out — that's expected, not an error, while waiting on propagation.

Full step-by-step instructions (registrar screenshots-in-words, HTTPS troubleshooting): [`docs/setup-guide.html`](docs/setup-guide.html) and [`docs/deployment.md`](docs/deployment.md).

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
| `linkedin-archive sync` fails with `403 Forbidden` | Your LinkedIn app hasn't been approved for member-social-read permissions yet (and, as of this writing, LinkedIn isn't approving new requests at all). Use `linkedin_export` or `import` instead. |
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

**Do I need LinkedIn API access to start?** No — and as of this writing you can't get it even if you wanted to (LinkedIn isn't granting `r_member_social` to new applicants). The sample provider works out of the box; for real content, `linkedin-archive import-export` against your own LinkedIn data export ([Importing existing posts](#importing-existing-posts)) is the recommended path, with JSON import as a manual fallback.

**Will this ever auto-delete my posts?** No. Posts that disappear from the source are kept by default (`sync.preserve_deleted: true` in `config.yaml`).

**Can I self-host instead of GitHub Pages?** Yes — `dist/` is a plain static site; deploy it anywhere (Netlify, Cloudflare Pages, S3, nginx).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
