"""Unit test for ``ContentRpcClient`` — the typed client for the content service.

Role in the system
------------------
``ServiceClient`` (tested in ``test_client.py``) speaks raw dicts. On top of it,
each service ships a *typed* client that knows that service's contracts.
``ContentRpcClient`` (in ``rpc/content_rpc/client.py``) wraps a ``ServiceClient``
and returns Pydantic models (``Project``, ``ProjectSummary``) instead of plain
JSON. It structurally implements the ``ContentSource`` Protocol, so the ai and
web services can depend on that Protocol and receive this concrete client via
dependency injection.

The testing pattern
-------------------
Same hermetic recipe as the base-client tests: inject an ``httpx.MockTransport``
so nothing hits the network. The handler here routes by request path to fake the
two content tools at once, letting a single test confirm that responses are
parsed into the correct typed models.
"""

import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient


def test_typed_client_parses_models():
    """Both content tools decode their JSON into the shared Pydantic contracts.

    The fake transport branches on ``request.url.path`` to serve ``get_project``
    (a single object) and ``list_projects`` (a list). We assert on
    ``.title``/``.slug`` attribute access — not dict keys — which proves the typed
    client validated and constructed real ``Project``/``ProjectSummary``
    instances. Those same contract classes are imported by callers, so a schema
    change would surface as a test/type failure on both sides.
    """
    def handler(request):
        # Route by path to emulate two distinct RPC tools with one handler.
        if request.url.path == "/rpc/get_project":
            return httpx.Response(200, json={"slug": "a", "title": "A", "body_html": "<p/>"})
        return httpx.Response(200, json=[{"slug": "a", "title": "A"}])
    # Compose the typed client over a ServiceClient bound to the fake transport.
    c = ContentRpcClient(ServiceClient("http://content", static_token_provider("t"),
                                       transport=httpx.MockTransport(handler)))
    assert c.get_project("a").title == "A"           # parsed into a Project
    assert c.list_projects(featured=True)[0].slug == "a"  # parsed into [ProjectSummary]
