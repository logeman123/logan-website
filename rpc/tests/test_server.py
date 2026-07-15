"""Unit tests for the server side of the RPC library (``rpc/server.py``).

Role in the system
------------------
Where ``test_client.py`` exercises the caller, this file exercises the *serving*
half that every microservice mounts:

* ``ToolRegistry`` — a decorator-based registry that maps a tool name to a
  handler function whose single argument is a Pydantic model. This is how a
  service declares its RPC/MCP surface.
* ``create_rpc_router`` — builds a FastAPI router that exposes each registered
  tool at ``POST /rpc/<tool>`` (plus ``GET /rpc/`` to list tools), enforces the
  shared bearer token, validates the JSON body against the handler's Pydantic
  model, and dispatches to the handler.
* ``add_rpc_error_handler`` — installs the exception->HTTP-status mapping so the
  RPCError hierarchy surfaces as the right status codes.

The testing pattern
-------------------
We build a tiny throwaway FastAPI app with two toy tools and drive it with
Starlette's ``TestClient``. ``TestClient`` calls the ASGI app in-process (no
socket, no running server), so these tests assert real routing, auth,
validation, and error mapping with zero network. The toy ``EchoIn`` model and
``echo``/``boom`` tools stand in for a real service's contracts and handlers —
the library behavior under test is identical regardless of which service uses it.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from rpc.server import ToolRegistry, create_rpc_router, add_rpc_error_handler
from rpc.exceptions import NotFound


class EchoIn(BaseModel):
    """A minimal request contract for the toy tools.

    In production each tool's argument model lives in an ``rpc/*_rpc`` package
    and is imported by both the service and its callers. Here a one-field model
    is enough to prove request validation works.
    """
    value: str


def _app(token="t"):
    """Assemble a throwaway service exposing two tools, wrapped in a TestClient.

    This mirrors exactly how a real service is wired: create a ``ToolRegistry``,
    register tools with the ``@reg.tool(name)`` decorator, install the error
    handler, then mount the generated RPC router with a shared bearer ``token``.
    Returning a ``TestClient`` lets each test issue HTTP-shaped requests that run
    entirely in-process against the ASGI app.
    """
    reg = ToolRegistry()

    @reg.tool("echo")
    def echo(args: EchoIn) -> dict:
        # A well-behaved tool: receives a validated ``EchoIn`` and returns JSON.
        return {"echo": args.value}

    @reg.tool("boom")
    def boom(args: EchoIn) -> dict:
        # A tool that deliberately raises an RPCError, to prove the error
        # handler maps ``NotFound`` -> HTTP 404 even from inside a handler.
        raise NotFound("gone")

    app = FastAPI()
    add_rpc_error_handler(app)  # register RPCError -> HTTP status mapping
    app.include_router(create_rpc_router(reg, token))  # mount POST /rpc/<tool>
    return TestClient(app)  # in-process ASGI driver; no real server/port


def test_dispatch_ok():
    """Happy path: a valid, authenticated call reaches the handler and its
    return value is serialized back as the JSON response body."""
    r = _app().post("/rpc/echo", json={"value": "hi"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json() == {"echo": "hi"}


def test_bad_token_is_401():
    """A wrong bearer token is rejected before dispatch with HTTP 401.

    The router checks the shared token first, so auth failures never reach a
    handler. This is the server counterpart to the client's ``AuthError`` -> 401
    mapping.
    """
    r = _app().post("/rpc/echo", json={"value": "hi"}, headers={"Authorization": "Bearer NOPE"})
    assert r.status_code == 401


def test_unknown_tool_is_404():
    """An unregistered tool name yields HTTP 404 (NotFound).

    The registry has no ``nope`` handler, so dispatch fails cleanly rather than
    500ing — the same status a missing resource would produce.
    """
    r = _app().post("/rpc/nope", json={}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_validation_error_is_400():
    """A body that doesn't satisfy the tool's Pydantic model yields HTTP 400.

    ``echo`` requires ``value``; sending ``{"wrong": 1}`` fails validation, which
    the error handler maps to ``InvalidRequest`` -> 400. Validation happens
    before the handler runs, so handlers can trust their typed argument.
    """
    r = _app().post("/rpc/echo", json={"wrong": 1}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 400


def test_handler_rpcerror_maps_status():
    """An RPCError raised *inside* a handler is mapped to its status code.

    ``boom`` raises ``NotFound``; the installed handler turns that into HTTP 404.
    This proves domain errors flow through with the correct status even when
    they originate deep in business logic — the whole point of pairing the
    exception hierarchy with a central error->status map.
    """
    r = _app().post("/rpc/boom", json={"value": "x"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_list_tools():
    """``GET /rpc/`` returns the registry's tool names for discovery.

    This introspection endpoint is what lets the AI service treat the RPC
    surface as an MCP-style tool catalog.
    """
    r = _app().get("/rpc/", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and "echo" in r.json()
