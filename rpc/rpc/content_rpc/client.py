"""Typed client for the **content** service, plus the ``ContentSource`` abstraction it fulfils.

This module is the caller-side half of content's RPC contract. It gives the rest of the system
two things:

1. ``ContentSource`` -- a structural ``Protocol`` that names the *capability* ("something that
   can list and fetch projects") without saying anything about HTTP. Callers (the web BFF, the
   ai service's tool loop) are typed against THIS, not against the concrete client below.

2. ``ContentRpcClient`` -- the concrete implementation that actually speaks HTTP+JSON RPC to the
   content service, and re-hydrates the raw JSON back into the shared Pydantic contract models.

How this realises dependency inversion
--------------------------------------
High-level code depends on the ``ContentSource`` abstraction; the low-level HTTP detail
(``ContentRpcClient``) also depends on that same abstraction by implementing it. ``deps.py`` in
the web service is the single place that picks the concrete implementation and injects it. Swap
in ``InMemoryContentRepository``-backed fake in tests and nothing else changes, because the fake
*structurally* satisfies ``ContentSource`` too (no explicit ``implements``/inheritance needed --
that's what "structural" Protocol typing buys you).

Where the network work happens
------------------------------
``ContentRpcClient`` holds a ``ServiceClient`` (from ``rpc.base``) and delegates the transport
to it. ``ServiceClient`` is itself fully injected -- its ``base_url``, ``token_provider`` and
httpx ``transport`` are all passed in, with no host baked in -- and it is what turns transport
failures into ``ServiceError`` so callers' ``except RPCError`` graceful-degradation paths fire
when content is unreachable. This client stays thin: call a tool, validate the result.
"""

from typing import Protocol

from rpc.base import ServiceClient

from .contracts import Project, ProjectSummary


class ContentSource(Protocol):
    """The capability contract for reading projects -- the abstraction callers depend on.

    This is a ``typing.Protocol``, so any object with matching method signatures satisfies it
    *structurally* -- no base class, no registration. That is exactly why the real
    ``ContentRpcClient`` (HTTP) and the test fakes are freely interchangeable: both simply "look
    like" a ``ContentSource``. The method shapes mirror content's two RPC tools one-to-one.
    """

    # ``...`` bodies are Protocol method *stubs*: they declare the signature/return type only.
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    def get_project(self, slug: str) -> Project: ...


class ContentRpcClient:
    """Concrete ``ContentSource`` that reaches the content service over RPC.

    It owns no data and no host information; it wraps an injected ``ServiceClient`` and simply
    maps each ``ContentSource`` method onto the corresponding remote tool, then validates the
    JSON response back into the shared contract models so callers get real typed objects.
    """

    def __init__(self, client: ServiceClient):
        # Store the injected transport. We keep a ref rather than constructing our own httpx
        # client so that base_url/token/transport (and, in tests, a MockTransport) are all
        # decided by whoever wires us up in deps.py -- dependency injection at the wire level.
        self._c = client

    def list_projects(self, featured=None):
        # POST /rpc/list_projects with the (optional) featured filter as the request body.
        # ``rows`` comes back as a list of plain dicts decoded from JSON...
        rows = self._c.call("list_projects", featured=featured)
        # ...so re-validate each one into a ProjectSummary. This is where the wire contract is
        # enforced on the caller side: a shape the server no longer honours would raise here.
        return [ProjectSummary.model_validate(r) for r in rows]

    def get_project(self, slug):
        # Single-project fetch: call get_project(slug=...) and hydrate the richer Project model
        # (summary fields + role/highlights/links/body_html) from the returned JSON dict.
        return Project.model_validate(self._c.call("get_project", slug=slug))
