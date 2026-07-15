"""Route for the site root ("/") — a minimal under-construction placeholder.

This is the simplest possible route and a good reference for the shape they all
share: define an ``APIRouter``, attach a handler with ``@router.get(...)``, and
return a rendered template. Unlike ``work`` and ``chat``, the home page shows no
dynamic data, so it needs NO ``Depends(...)`` on an RPC client and cannot fail
due to a back-end being down — it just renders a static template.
"""

from fastapi import APIRouter, Request

from ..templating import templates

# Local router; main.py mounts it onto the app via app.include_router(home.router).
router = APIRouter()


@router.get("/")
def home(request: Request):
    """Render the landing page.

    ``request`` is required as the first positional argument to
    ``TemplateResponse`` under the Starlette 1.3.1 API (see templating.py). The
    empty ``{}`` is the template context — the placeholder page needs no
    variables, but the argument is passed explicitly for consistency with the
    other, data-driven routes.
    """
    return templates.TemplateResponse(request, "index.html", {})
