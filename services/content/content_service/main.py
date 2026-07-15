"""ASGI entry point for the content service — wires the pieces into one app.

This is the file ``uvicorn`` runs (``content_service.main:app``, on port 8001).
It is deliberately tiny: all the real logic lives in the repository, tools, and
the shared ``rpc`` library. ``main.py`` just performs the final assembly of the
dependency-injection graph:

    settings + repository  ->  tools (ToolRegistry)  ->  RPC router  ->  FastAPI

Notably, this module contains no data logic and no HTTP-dispatch logic of its
own; the ``rpc`` library provides both (routing/validation via
``create_rpc_router`` and error-to-status mapping via ``add_rpc_error_handler``),
so every microservice's ``main.py`` looks nearly identical. That uniformity is
the reward for pushing the cross-cutting concerns into the shared library.
"""

from fastapi import FastAPI

# Shared RPC plumbing, reused by all three services:
#   * add_rpc_error_handler — maps the RPCError hierarchy to HTTP status codes
#     (InvalidRequest=400, AuthError=401, NotFound=404, ServiceError=500), using
#     each exception's own `status_code`. This is what turns the NotFound raised
#     deep in the repository into a clean 404 for the caller.
#   * create_rpc_router — turns a ToolRegistry into POST /rpc/<tool> endpoints
#     plus a GET /rpc/ discovery listing, and enforces the bearer token.
from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_repository, get_settings
from .tools import build_content_registry

# The application object uvicorn imports and serves.
app = FastAPI(title="content")
# Register the exception handler FIRST so every route below inherits the
# RPCError -> HTTP status translation (callers rely on these codes to degrade).
add_rpc_error_handler(app)
# The full DI wiring in one line, read inside-out:
#   1. get_repository()                 -> the concrete FileContentRepository
#   2. build_content_registry(repo)     -> a ToolRegistry with that repo injected
#   3. create_rpc_router(registry, tok) -> a router exposing the tools at /rpc/*,
#      guarded by the shared service_token from settings
#   4. app.include_router(...)          -> mount those endpoints on the app
app.include_router(create_rpc_router(build_content_registry(get_repository()), get_settings().service_token))


@app.get("/health")
def health():
    """Liveness probe used by docker-compose / honcho / uptime checks.

    Intentionally trivial and unauthenticated: it takes no dependencies and
    touches no data, so a 200 here means "the process is up and serving HTTP",
    independent of whether the project files are readable.
    """
    return {"status": "ok"}
