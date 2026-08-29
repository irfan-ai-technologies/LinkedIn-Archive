"""A tiny local HTTP server that captures LinkedIn's OAuth redirect.

FastAPI is used here specifically because this is the one place in the
application that genuinely needs an HTTP server/API surface: LinkedIn
redirects the user's browser back to ``http://localhost:<port>/callback``
with a ``code`` and ``state`` query parameter after they approve access.
Everything else in LinkedIn Archive is a static site with no server
component.

The server binds to localhost only, serves exactly one useful request, and
shuts itself down immediately afterward.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

_SUCCESS_HTML = """
<!doctype html><html><head><title>LinkedIn Archive</title></head>
<body style="font-family: sans-serif; max-width: 32rem; margin: 4rem auto;">
<h1>Authorization received</h1>
<p>You can close this tab and return to your terminal.</p>
</body></html>
"""

_ERROR_HTML = """
<!doctype html><html><head><title>LinkedIn Archive</title></head>
<body style="font-family: sans-serif; max-width: 32rem; margin: 4rem auto;">
<h1>Authorization failed</h1>
<p>{message}</p>
</body></html>
"""


@dataclass
class CallbackResult:
    code: str | None = None
    state: str | None = None
    error: str | None = None


def await_oauth_callback(redirect_uri: str, timeout: float = 300.0) -> CallbackResult:
    """Start a local server, wait for the OAuth redirect, then stop.

    Blocks the calling thread until the callback is received or ``timeout``
    seconds elapse.
    """
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8765
    path = parsed.path or "/callback"

    result = CallbackResult()
    received = threading.Event()

    app = FastAPI()

    @app.get(path)
    def callback(
        request: Request,
    ) -> HTMLResponse:  # pragma: no cover - exercised via TestClient in tests
        params = request.query_params
        result.code = params.get("code")
        result.state = params.get("state")
        result.error = params.get("error_description") or params.get("error")
        received.set()
        if result.error:
            return HTMLResponse(_ERROR_HTML.format(message=result.error), status_code=400)
        return HTMLResponse(_SUCCESS_HTML)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        received.wait(timeout=timeout)
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    if not received.is_set():
        result.error = f"Timed out waiting for LinkedIn redirect on {redirect_uri}"
    return result
