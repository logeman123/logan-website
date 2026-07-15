"""ASGI entrypoint for the **ai** service — assembles the FastAPI app.

This module is deliberately tiny: it does no business logic itself, it just *composes* the
pieces that other modules define. Run it with e.g. ``uvicorn ai_service.main:app`` (honcho's
Procfile.dev does this on port 8002). The three lines below capture the whole service:

    1. Create the FastAPI app.
    2. Install the RPC error handler (maps the RPCError hierarchy to HTTP status codes).
    3. Build the tool registry, turn it into a router, and mount it — auth-guarded by the
       shared service token.

Note how everything concrete comes from deps.py (dependency injection): main.py never
imports Chat, an LLM, or a content client directly — it asks deps for a fully-wired object.
"""

from fastapi import FastAPI

# From the shared rpc library:
# * add_rpc_error_handler — registers exception handlers so raised RPCError subclasses become
#   the right HTTP status (InvalidRequest=400, AuthError=401, NotFound=404, ServiceError=500)
#   via each exception's status_code, instead of a generic 500.
# * create_rpc_router — builds a FastAPI router that exposes each registered tool at
#   POST /rpc/<tool> (and lists them at GET /rpc/), enforcing the bearer-token auth.
from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_chat, get_settings
from .rpc_tools import build_ai_registry

# The ASGI application object uvicorn serves. title="ai" just labels it in the OpenAPI docs.
app = FastAPI(title="ai")
# Wire the RPC-error -> HTTP-status mapping into this app (see comment above).
add_rpc_error_handler(app)
# Assemble and mount the RPC surface in one expression, reading inside-out:
#   get_chat()            -> a fully-wired Chat (agentic loop, LLM + content already injected)
#   build_ai_registry(..) -> a ToolRegistry advertising the "chat" tool
#   create_rpc_router(..) -> a FastAPI router for those tools, guarded by the service token
#   app.include_router(..) -> attach it, so POST /rpc/chat is now live.
app.include_router(create_rpc_router(build_ai_registry(get_chat()), get_settings().service_token))


@app.get("/health")
def health():
    # Trivial, unauthenticated liveness probe used by orchestration / compose healthchecks
    # to confirm the process is up (distinct from the token-guarded /rpc surface).
    return {"status": "ok"}
