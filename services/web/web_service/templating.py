"""Shared Jinja2 template environment for the web BFF.

Every route module imports the single ``templates`` object defined here rather
than constructing its own. Centralizing it means all routes render from the same
``templates/`` directory with one consistent configuration, and there is exactly
one place to change template settings later.

Usage note (Starlette 1.3.1 API): handlers call
``templates.TemplateResponse(request, name, context)`` — the ``request`` is the
FIRST positional argument. This is the modern signature; older tutorials pass the
context dict with ``{"request": request, ...}`` inside it, which is now
deprecated. Passing ``request`` explicitly lets Jinja expose request-aware
helpers (like ``url_for``) inside templates.
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

# Point Jinja at the "templates" directory that sits next to this file. Building
# the path from ``Path(__file__).parent`` (rather than a relative string) makes
# template discovery independent of the process's current working directory, so
# it resolves correctly whether launched by honcho, uvicorn, docker, or pytest.
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
