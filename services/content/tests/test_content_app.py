"""Integration tests for the content service's RPC/HTTP surface.

Where ``test_repository.py`` tested the repository *object* directly, this
module tests the thin HTTP layer that exposes that repository over the shared
RPC convention:

    * ``build_content_registry`` binds the repo's operations to named tools
      (get_project, list_projects) in a ``ToolRegistry``.
    * ``create_rpc_router`` turns that registry into FastAPI routes at
      ``POST /rpc/<tool>`` (and a discovery ``GET /rpc/``), decoding the JSON
      body into the tool's pydantic input and encoding the result back to JSON.
    * ``add_rpc_error_handler`` installs the one handler that maps the shared
      RPCError hierarchy onto HTTP status codes (NotFound -> 404, etc.).

Key idea being demonstrated: the SAME RPC surface that the web BFF calls is
also the surface the AI service calls as MCP-style "tools". We test it here by
building a tiny throwaway FastAPI app wired to an in-memory fake repo, so no
disk or network is involved -- only the request/response contract matters.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rpc.content_rpc.contracts import Project
from rpc.server import create_rpc_router, add_rpc_error_handler
from content_service.repository import InMemoryContentRepository
from content_service.tools import build_content_registry

# A single seed project used across the tests. Building it from the shared
# ``Project`` contract (not a dict) means the fake repo returns exactly the
# type the real repo would.
P = Project(slug="a", title="A", blurb="b", featured=True, body_html="<p>x</p>")


def _client():
    """Assemble a minimal, self-contained content app around the fake repo.

    This mirrors how the real content service is wired in production, but
    substitutes ``InMemoryContentRepository`` for the file-backed one (dependency
    inversion again -- the RPC layer neither knows nor cares which repo it got).
    The three lines are the entire "assembly recipe" for an RPC service:

        1. add the RPCError -> HTTP status handler,
        2. build the tool registry from the repo,
        3. mount it as ``/rpc/*`` routes guarded by the bearer token ``"t"``.
    """
    app = FastAPI()
    add_rpc_error_handler(app)  # RPCError subclasses become their status_code responses
    # The trailing "t" is the expected bearer token; requests must send
    # ``Authorization: Bearer t`` or the router rejects them with a 401.
    app.include_router(create_rpc_router(build_content_registry(InMemoryContentRepository([P])), "t"))
    return TestClient(app)  # Starlette's in-process HTTP client -- no real socket


def test_get_project_ok():
    # Happy path: POST the tool's JSON input to /rpc/<tool>, with the bearer
    # token the router expects. A 200 plus the round-tripped title proves the
    # full decode -> dispatch -> encode pipeline works end to end.
    r = _client().post("/rpc/get_project", json={"slug": "a"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json()["title"] == "A"


def test_get_project_missing_404():
    # The repo raises ``NotFound`` for an unknown slug; the RPC error handler is
    # what turns that domain exception into HTTP 404. This test is really
    # asserting the exception -> status mapping, exercised over real HTTP.
    r = _client().post("/rpc/get_project", json={"slug": "z"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_list_featured():
    # The ``featured`` filter flows through the JSON body into the tool's typed
    # input and down to the repo. Our lone seed project is featured, so it is
    # the only slug returned.
    r = _client().post("/rpc/list_projects", json={"featured": True}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and [p["slug"] for p in r.json()] == ["a"]
