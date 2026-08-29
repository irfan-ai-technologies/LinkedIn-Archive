"""A tiny local static file server for previewing ``dist/``."""

from __future__ import annotations

import functools
import http.server
from pathlib import Path


def serve_directory(
    directory: Path, host: str = "127.0.0.1", port: int = 8000, base_path: str = ""
) -> None:
    """Serve ``directory`` at ``http://host:port<base_path>/``.

    The build bakes ``base_path`` (derived from ``site.url``) into every
    internal link and asset path, so the dev server strips it back off
    incoming requests to map them onto ``directory`` — this way a project
    site (``site.url`` with a path, e.g. a GitHub Pages repo site) previews
    the same way it will actually be served, not at the domain root.
    """
    base_path = base_path.rstrip("/")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            if base_path and (path == base_path or path.startswith(f"{base_path}/")):
                path = path[len(base_path) :] or "/"
            return super().translate_path(path)

    handler = functools.partial(Handler, directory=str(directory))
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving {directory} at http://{host}:{port}{base_path}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
