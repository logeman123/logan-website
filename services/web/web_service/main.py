"""ASGI application entry point for the web BFF (served on port 8000).

This is the file uvicorn/honcho load as ``web_service.main:app``. Its whole job
is assembly: create the FastAPI ``app``, mount static assets, and stitch in the
per-area routers from the ``routes`` package. It deliberately contains almost no
logic of its own — the interesting behavior lives in the routers (which call the
content/ai services over RPC) and in ``deps.py`` (which wires up those clients).

Unlike the content and ai services, this app registers no ``/rpc`` surface and no
RPC error handler: the web service is a *consumer* of RPC, not a *provider* of
it. It speaks HTML to browsers, not JSON-RPC to peers.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Import the four route modules; each exposes an ``APIRouter`` named ``router``.
from .routes import chat, home, resume, work

# Directory containing this file, used below to locate the sibling "static" dir
# regardless of the process's working directory.
BASE = Path(__file__).parent
# The ASGI application object. ``title`` shows up in the auto-generated OpenAPI
# docs and distinguishes this app from the "content" and "ai" FastAPI apps.
app = FastAPI(title="web")
# Serve CSS/JS/images straight from disk under /static (e.g. the resume page's
# retro styling and the HTMX/Alpine libraries the templates pull in).
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
# Register each area's routes onto the single app. Order here does not affect
# matching because the paths ("/", "/work", "/chat", "/resume") don't overlap.
app.include_router(home.router)
app.include_router(work.router)
app.include_router(chat.router)
app.include_router(resume.router)


@app.get("/health")
def health():
    """Liveness probe used by orchestrators (docker-compose, load balancers).

    Returns a trivial static payload with no dependency on content/ai, so it
    reports whether *this* process is up without being affected by whether the
    back-ends are reachable.
    """
    return {"status": "ok"}
