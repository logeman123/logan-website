"""Routes for the "work" area — a project list and per-project detail pages.

These two handlers are the clearest illustration of the BFF pattern in action:
the web service owns none of this data, so both routes fetch it from the CONTENT
service over RPC via the injected ``ContentSource`` client, then render it into
HTML.

Two cross-cutting patterns to notice:

  1. Graceful degradation. Every RPC call is wrapped in ``try/except RPCError``.
     The ``ServiceClient`` in the rpc library converts a down/unreachable content
     service (and any 4xx/5xx it returns) into an ``RPCError`` subclass, so these
     handlers can catch that and render a friendly fallback page instead of
     letting the request 500. A back-end outage degrades the page, never crashes
     it.

  2. Exception ordering. In ``work_detail`` the ``except NotFound`` clause is
     listed BEFORE ``except RPCError``. ``NotFound`` is a *subclass* of
     ``RPCError``, and Python matches except-clauses top to bottom, so the
     specific case (missing slug -> real HTTP 404) must come first; otherwise the
     broad ``RPCError`` clause would swallow it and we'd wrongly report a generic
     outage for a simply-nonexistent project.
"""

from fastapi import APIRouter, Depends, Request

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import NotFound, RPCError

from ..deps import get_content
from ..templating import templates

router = APIRouter()


@router.get("/work")
def work_list(request: Request, content: ContentSource = Depends(get_content)):
    """List all projects.

    ``content`` is injected by FastAPI from ``get_content`` (see deps.py) and
    typed only as the ``ContentSource`` Protocol — this handler neither knows nor
    cares that behind the interface sits an HTTP client hitting port 8001.
    """
    try:
        # RPC hop: web -> content service's /rpc/list_projects tool.
        projects = content.list_projects()
        error = None
    except RPCError:
        # Content service unreachable or erroring: degrade to an empty list plus
        # a banner message. The page still renders 200, never 500.
        projects, error = [], "Work is temporarily unavailable."
    return templates.TemplateResponse(request, "work_list.html", {"projects": projects, "error": error})


@router.get("/work/{slug}")
def work_detail(slug: str, request: Request, content: ContentSource = Depends(get_content)):
    """Show one project by its URL ``slug``.

    The three-way branch below is deliberate and order-sensitive (see the module
    docstring): a genuinely missing project yields a real 404, a back-end problem
    yields a soft "temporarily unavailable" page, and the happy path renders the
    project.
    """
    try:
        # RPC hop: web -> content service's /rpc/get_project tool.
        project = content.get_project(slug)
    except NotFound:
        # Specific case FIRST: the slug doesn't exist. Render the detail template
        # in its empty state and set a true HTTP 404 so crawlers/clients know the
        # resource is genuinely absent (not merely temporarily broken).
        return templates.TemplateResponse(
            request, "work_detail.html", {"project": None, "error": None}, status_code=404)
    except RPCError:
        # Broader case SECOND: content service down/erroring. Degrade gracefully
        # with a 200 fallback page and an explanatory message.
        return templates.TemplateResponse(
            request, "work_detail.html", {"project": None, "error": "Temporarily unavailable."})
    # Happy path: hand the fetched project to the template for full rendering.
    return templates.TemplateResponse(request, "work_detail.html", {"project": project, "error": None})
