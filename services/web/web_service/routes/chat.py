"""Routes for the chat UI — a two-endpoint HTMX flow backed by the ai service.

The chat feature is split into a full page and a partial:

  GET /chat  -> returns the whole ``chat.html`` page (shell + input form).
  POST /chat -> returns ONLY the ``_chat_reply.html`` fragment (one Q&A bubble).

This is the HTMX partial-swap pattern. The form in ``chat.html`` posts to
``/chat`` via HTMX, and HTMX splices the returned HTML fragment into the page's
message list WITHOUT a full navigation or a client-side framework. The leading
underscore in ``_chat_reply.html`` is a convention marking it as a partial meant
to be embedded, not served as a standalone page.

The interesting hop happens inside ``ai.chat(...)``: this handler calls the AI
service over RPC, and the ai service in turn runs an agentic tool-use loop that
may call BACK into the content service's RPC tools (get_project / list_projects)
to ground its answer in real project data. So one POST can fan out
web -> ai -> content, all over the same JSON-RPC surface. The web service itself
stays blissfully unaware of that; it just awaits a ``reply`` string.
"""

from fastapi import APIRouter, Depends, Form, Request

from rpc.ai_rpc.client import AiSource
from rpc.exceptions import RPCError

from ..deps import get_ai
from ..templating import templates

router = APIRouter()


@router.get("/chat")
def chat_page(request: Request):
    """Serve the full chat page shell.

    No RPC and no context dict needed — this just returns the static page that
    hosts the HTMX-powered form. Actual answers arrive via POST /chat below.
    """
    return templates.TemplateResponse(request, "chat.html")


@router.post("/chat")
def chat_send(request: Request, message: str = Form(...), ai: AiSource = Depends(get_ai)):
    """Handle a submitted message and return the reply as an HTML fragment.

    ``message`` is pulled from the posted form body via ``Form(...)`` (the "..."
    marks it required). ``ai`` is injected from ``get_ai`` (deps.py) and typed as
    the ``AiSource`` Protocol, so this handler depends on the interface, not on
    the concrete HTTP client.
    """
    try:
        # RPC hop: web -> ai service's /rpc/chat tool. ``.reply`` pulls the answer
        # text off the typed response object. Inside the ai service this call may
        # itself trigger further RPC calls into content (the agentic tool loop).
        reply = ai.chat(message=message).reply
    except RPCError:
        # Graceful degradation: if the ai service is down/erroring, substitute a
        # friendly message so the chat UI still swaps in a coherent bubble rather
        # than showing an error or 500.
        reply = "The chat is temporarily unavailable — please try again shortly."
    # Return only the partial. HTMX inserts this fragment into the existing page;
    # we echo the user's ``message`` back so the template can render both sides of
    # the exchange in one bubble.
    return templates.TemplateResponse(request, "_chat_reply.html", {"message": message, "reply": reply})
