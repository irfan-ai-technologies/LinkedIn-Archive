# Security Policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a security vulnerability. Instead, use GitHub's private vulnerability reporting (repository **Security → Advisories → Report a vulnerability**), or contact the repository owner directly. Include:

- A description of the issue and its potential impact.
- Steps to reproduce (a minimal repro is ideal).
- Any relevant version/commit information.

## Scope and design notes for reviewers

- **No LinkedIn scraping or credential storage.** LinkedIn integration (`app/ingestion/linkedin.py`, `app/ingestion/linkedin_oauth.py`) uses only LinkedIn's official OAuth 2.0 authorization code flow. No password is ever requested or stored.
- **Tokens never enter the repository.** OAuth tokens are written to a path outside version control (`.secrets/` by default, gitignored) or provided via GitHub Secrets in CI. They are never logged (`app/ingestion/linkedin_oauth.py` deliberately omits response bodies from error messages) and never written into generated content.
- **Post content is treated as untrusted input.** Every post body — regardless of provider — is rendered through `app/site/render.py`, which uses `bleach` to strip scripts, event handler attributes, and non-http(s)/mailto URL schemes before HTML reaches a page.
- **Filenames are derived safely.** Post IDs are slugified (`app/storage/store.py`) and raw-archive filenames are character-filtered (`app/storage/raw_archive.py`) to prevent path traversal from untrusted source identifiers.
- **No arbitrary code execution.** Content is never `eval`'d, and Markdown rendering has no plugin surface enabled beyond CommonMark + linkify.

If you believe any of the above guarantees don't hold in some case, that's exactly what we want to hear about.
