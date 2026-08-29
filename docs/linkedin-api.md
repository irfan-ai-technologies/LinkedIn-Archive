# LinkedIn API setup

LinkedIn Archive integrates with LinkedIn **only** through LinkedIn's official OAuth 2.0 API. It does not scrape LinkedIn, does not automate a browser, and does not store your LinkedIn password. If you don't want to deal with LinkedIn's app-review process right now, skip straight to using the `sample` or `import` provider — the rest of the product works identically either way.

## The permission LinkedIn requires

Reading a member's own posts requires LinkedIn's **member-social-read** permissions (for example, the `r_member_social` scope), which are part of a **restricted product** on LinkedIn's developer platform. Restricted products require LinkedIn to review and approve your application before the scope is usable — this is a policy on LinkedIn's side, not a limitation of this project, and there is no way around it. Approval timelines and requirements are set by LinkedIn and can change; always check LinkedIn's current developer documentation rather than relying solely on this file.

Until approval is granted, any sync attempt against the `linkedin` provider will fail with a clear `403 Forbidden` error rather than silently doing something else.

## Step 1 — create a LinkedIn app

1. Go to LinkedIn's developer portal and create a new app, associated with a Company Page you administer (LinkedIn requires this).
2. Under the app's **Auth** tab, note the **Client ID** and **Client Secret**.
3. Add an **Authorized redirect URL**. For local use, this is `http://localhost:8765/callback` (matching `LINKEDIN_REDIRECT_URI` in `.env.example`). For CI/automated sync, you authorize once locally and reuse the resulting token — the redirect URL only needs to work for that one interactive login.
4. Under **Products**, request the product(s) that grant member-social-read access (member-social scopes such as `r_member_social`). This is the step that requires LinkedIn's review/approval.

## Step 2 — configure local secrets

```bash
cp .env.example .env
```

Fill in:

```
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=http://localhost:8765/callback
```

Never commit `.env`. It's already in `.gitignore`.

## Step 3 — authorize once, locally

```bash
uv run linkedin-archive auth login
```

This opens your browser to LinkedIn's consent screen, starts a short-lived local server (`app/ingestion/linkedin_auth_server.py`, built with FastAPI — the one place in this project that needs an HTTP server) to catch the redirect, exchanges the authorization code for an access token, and saves it to `.secrets/linkedin_token.json` (gitignored, `chmod 600`).

## Step 4 — sync

```bash
uv run linkedin-archive sync --provider linkedin
```

Or set `sync.provider: linkedin` in `config.yaml` and just run `linkedin-archive sync`.

## Refresh tokens

If your app has been granted LinkedIn's `offline_access` product, LinkedIn issues a refresh token alongside the access token; `LinkedInProvider` uses it automatically when the access token expires (`app/ingestion/linkedin.py`). If your app wasn't granted that product, re-run `auth login` when the token expires — you'll get a clear error message telling you to do so rather than a confusing failure.

## Using this in GitHub Actions

You cannot complete the interactive OAuth flow inside a GitHub Actions runner (there's no browser). The pattern is:

1. Run `auth login` locally once.
2. Copy the contents of `.secrets/linkedin_token.json`.
3. Store it as a repository secret named `LINKEDIN_TOKEN_JSON`, along with `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`.
4. `.github/workflows/sync.yml` restores it to `.secrets/linkedin_token.json` before running sync, and removes it afterward. As long as your app has `offline_access`, the refresh token keeps this working indefinitely; otherwise, repeat this process when the access token expires.

## Isolation

All of the above — endpoints, request/response shapes, API version headers — lives in `app/ingestion/linkedin.py` and `app/ingestion/linkedin_oauth.py`. If LinkedIn changes its API, this is the only file that needs to change; nothing in `app/site/`, `app/search/`, or `app/enrichment/` depends on LinkedIn's API shape.

## What this project will never do

- Scrape LinkedIn's website or API without using the documented OAuth flow.
- Automate a browser session logged in as you.
- Ask for or store your LinkedIn password.
- Attempt to bypass LinkedIn's restricted-product approval process.

If you need posts sooner than LinkedIn's approval process allows — or if it never comes through,
since LinkedIn is not currently accepting new `r_member_social` access requests at all — use
`linkedin-archive import-export <unzipped export dir>` against LinkedIn's own "Download my data"
export, or hand-write `linkedin-archive import posts.json`. See [`providers.md`](providers.md).
