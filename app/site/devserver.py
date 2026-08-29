"""A tiny local static file server for previewing ``dist/``."""

from __future__ import annotations

import functools
import http.server
from pathlib import Path


def serve_directory(directory: Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving {directory} at http://{host}:{port}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
