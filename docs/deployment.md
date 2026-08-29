# Deployment

## GitHub Pages (recommended default)

1. **Settings → Pages → Source: GitHub Actions.**
2. Push to `main`, or run **Actions → Deploy site → Run workflow**.
3. `deploy.yml` installs dependencies with `uv`, runs `linkedin-archive validate`, then `linkedin-archive build`, uploads `dist/` as a Pages artifact, and deploys it. `dist/` is never committed to the repository — it's rebuilt fresh on every deploy (see `docs/architecture.md` for why).
4. Your site is live at `https://<you>.github.io/<repo>/` (or `https://<you>.github.io/` for a repo named `<you>.github.io`).

Set `site.url` in `config.yaml` to match this URL (or your custom domain, below) — it's used for canonical links, the sitemap, and the RSS feed.

## Custom domain

1. Buy/own a domain (any registrar).
2. Add DNS records at your registrar or DNS provider:
   - **Apex domain** (`example.com`): four `A` records pointing at GitHub Pages' IPs (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`), plus `AAAA` records if you want IPv6 (`2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`).
   - **Subdomain** (`archive.example.com`): a `CNAME` record pointing at `<you>.github.io`.
3. In the repo, **Settings → Pages → Custom domain**, enter your domain, save. GitHub writes a `CNAME` file into the Pages deployment automatically when you do this through the UI — but since this project builds `dist/` fresh every time rather than committing it, the safer approach is to commit the domain yourself: create `static/CNAME` containing just your domain name (e.g. `archive.example.com`), so it's copied into `dist/CNAME` on every build.
4. Check **Enforce HTTPS** once GitHub finishes issuing a certificate (can take a few minutes to a few hours after DNS propagates).
5. Update `site.url` in `config.yaml` to `https://your-domain`.

For the fully detailed, click-by-click version (including where to find these settings and what to expect at each step), see [`setup-guide.html`](setup-guide.html).

## Self-hosting elsewhere

`dist/` is a plain static site — no server-side code, no environment-specific paths beyond what's baked in at build time. Deploy it to Netlify, Cloudflare Pages, S3 + CloudFront, or any static file host:

```bash
uv run linkedin-archive build
# upload the contents of dist/ to your host of choice
```

Set `site.url` in `config.yaml` to that host's URL before building, since it's baked into canonical links, the sitemap, and RSS at build time.

## Verifying a deployment

```bash
uv run linkedin-archive validate   # content/config sanity
uv run linkedin-archive build      # regenerate dist/
uv run linkedin-archive serve      # preview locally before pushing
```

Check: home page loads, a post page opens directly, `/search/` returns results, `/feed.xml` and `/sitemap.xml` are well-formed, dark/light mode toggles, and the layout is usable on a narrow viewport.
