# Customizing the theme

No build step, no frontend framework — edit files and rebuild.

## Templates

`app/site/templates/` (Jinja2):

```
base.html                  # <head>, header, footer — every page extends this
partials/post_card.html    # the card used on home/listing pages (Jinja macro)
partials/pagination.html   # pagination controls (Jinja macro)
pages/home.html
pages/about.html
pages/post.html
pages/posts_index.html
pages/category_index.html
pages/category.html
pages/tag_index.html
pages/tag.html
pages/archive_index.html
pages/archive_year.html
pages/archive_month.html
pages/search.html
pages/404.html
```

Every template has access to these Jinja globals (set once in `app/site/generator.py`, `SiteGenerator._build_environment`): `site`, `theme`, `config`, `profile`, `category_slug_map`, and every `*_url()` helper from `app/site/urls.py`. Two filters are registered: `render_markdown` and `format_date`.

## Styles

`static/css/style.css` — a single stylesheet, CSS custom properties for theming (`:root` for light, `[data-theme="dark"]` + `prefers-color-scheme` for dark). Change `--accent`, `--bg`, `--text`, etc. to re-theme without touching any template.

## Behavior

`static/js/`:

- `theme.js` — dark/light toggle, persisted to `localStorage`.
- `nav.js` — the `/` keyboard shortcut to focus search.
- `search.js` — the client-side search engine (fetches `search-index.json`, tokenizes the query, scores/filters/sorts, renders results). See [`configuration.md`](configuration.md) for `search.max_indexed_chars`.

All three are vanilla ES5-ish JavaScript with no build step and no dependencies.

## Adding a new page

1. Add a template under `app/site/templates/pages/`.
2. Add a URL helper to `app/site/urls.py` if it needs a stable, linkable path.
3. Add a `_write_*` method to `SiteGenerator` (`app/site/generator.py`) that renders it.
4. If it should be crawlable, add it to the sitemap entries in `SiteGenerator._write_feeds`.

## Changing pagination/listing sizes

`theme.posts_per_page`, `theme.featured_count`, `theme.recent_count`, `pagination.posts_per_page`, `pagination.archive_per_page` in `config.yaml` — no code changes.
