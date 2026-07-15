"""Unit tests for ``ServiceClient`` — the shared, injectable RPC wire client.

Role in the system
------------------
``ServiceClient`` (in ``rpc/base.py``) is the thin ``httpx`` wrapper that every
service uses to talk to every other service. It is the "wire level" of the
dependency-inversion story: its ``base_url``, ``token_provider``, and
``transport`` are ALL injected by the caller — nothing about a concrete host or
network is baked in. That single design choice is what makes these tests fast
and hermetic.

The key testing pattern
-----------------------
We never open a real socket. Instead we inject an ``httpx.MockTransport`` whose
``handler`` function receives the outgoing ``httpx.Request`` and returns a
canned ``httpx.Response`` (or raises a transport error). Because the transport
is a constructor argument, the test can substitute a fake at exactly the seam
where real network I/O would otherwise happen — so every assertion below runs
with ZERO network access. This is dependency injection used purely for
testability: the production code path is identical; only the transport differs.

Each test isolates one behavior of the client: header/serialization, HTTP
status -> exception mapping, transport-error -> ServiceError wrapping, and token
caching.
"""

import json
import httpx
import pytest
from rpc.base import ServiceClient, static_token_provider
from rpc.exceptions import NotFound, ServiceError


def _client(handler, token="t"):
    """Build a ``ServiceClient`` wired to a fake in-memory transport.

    ``handler`` is a plain function ``(httpx.Request) -> httpx.Response`` that
    stands in for the remote service. Wrapping it in ``httpx.MockTransport`` and
    passing it as the ``transport=`` argument means the client's real request
    pipeline runs (headers, JSON body, URL building, error mapping) but the
    bytes never leave the process. ``static_token_provider(token)`` supplies a
    fixed bearer token so we can assert on the ``Authorization`` header.
    """
    return ServiceClient("http://svc", static_token_provider(token),
                         transport=httpx.MockTransport(handler))


def test_call_sends_bearer_and_returns_json():
    """The happy path: a call serializes kwargs to JSON, attaches the bearer
    token, targets ``/rpc/<tool>``, and returns the decoded JSON body.

    The handler doubles as an assertion site: it inspects the request the client
    actually built. This proves the wire contract shared by every service —
    ``POST /rpc/<tool>`` with a JSON body and ``Authorization: Bearer <token>``.
    """
    def handler(request):
        # Client must inject the bearer token from the token provider.
        assert request.headers["authorization"] == "Bearer t"
        # kwargs passed to the dynamic method become the JSON request body.
        assert json.loads(request.content) == {"slug": "x"}
        # The attribute name (``get_project``) maps to the RPC tool path.
        assert request.url.path == "/rpc/get_project"
        return httpx.Response(200, json={"slug": "x", "ok": True})
    # ``get_project`` is not a defined method — ServiceClient resolves unknown
    # attributes dynamically into ``call("get_project", ...)``, so any tool name
    # works without hand-writing a method.
    assert _client(handler).get_project(slug="x") == {"slug": "x", "ok": True}


def test_error_status_maps_to_exception():
    """A non-2xx HTTP status is translated into the matching RPCError subclass.

    Here the server "returns" 404, and the client raises ``NotFound``. This is
    the client-side half of the error<->status contract: the same status codes
    the server maps FROM exceptions, the client maps BACK INTO exceptions, so
    callers can ``except NotFound`` regardless of transport details.
    """
    def handler(request):
        return httpx.Response(404, text="nope")
    with pytest.raises(NotFound):
        _client(handler).get_project(slug="missing")


def test_connect_error_maps_to_service_error():
    """A transport-level failure (unreachable backend) becomes ``ServiceError``.

    We simulate an unreachable host by having the handler raise
    ``httpx.ConnectError``. The client wraps it as ``ServiceError`` (a subclass
    of ``RPCError``). This is what enables graceful degradation upstream: web/ai
    routes catch ``RPCError`` and render fallbacks instead of crashing when a
    dependency is down.
    """
    def handler(request):
        raise httpx.ConnectError("boom")
    with pytest.raises(ServiceError):
        _client(handler).call("x")


def test_token_is_cached():
    """The token provider is consulted once and its token reused until expiry.

    A ``token_provider`` returns ``(token, expiry_epoch_seconds)``. Here the
    provider counts its own invocations. After two RPC calls the counter is 1,
    proving the client caches the token rather than re-authenticating on every
    request — an important efficiency property for chatty service-to-service
    traffic.
    """
    calls = {"n": 0}
    def provider():
        calls["n"] += 1
        return "tok", 3600.0  # token valid for an hour -> should be cached
    def handler(request):
        return httpx.Response(200, json={})
    c = ServiceClient("http://svc", provider, transport=httpx.MockTransport(handler))
    c.call("a")
    c.call("b")
    assert calls["n"] == 1  # provider invoked once despite two calls
