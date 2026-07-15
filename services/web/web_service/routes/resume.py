"""Route for "/resume" — a standalone, hand-built retro "jungle"-themed page.

This route is intentionally self-contained: like ``home``, it takes NO RPC
dependency and pulls no data from the content/ai services. All of its content and
its distinctive retro styling live in the ``resume.html`` template and the static
assets. The signature flourish is that its section headers "reveal" from Egyptian
hieroglyphs into readable text via Alpine.js directives embedded in that
template — so the animation is entirely client-side, and this handler's only job
is to deliver the page.
"""

from fastapi import APIRouter, Request

from ..templating import templates

router = APIRouter()


@router.get("/resume")
def resume(request: Request):
    """Render the retro jungle-themed resume page.

    A plain static render: ``request`` first (Starlette 1.3.1 signature) and an
    empty context dict, since the template supplies everything itself.
    """
    return templates.TemplateResponse(request, "resume.html", {})
