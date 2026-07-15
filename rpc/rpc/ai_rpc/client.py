"""Typed client for the **ai** service, plus the ``AiSource`` abstraction it fulfils.

Caller-side half of the ai contract, and a direct parallel to ``content_rpc.client``:

1. ``AiSource`` -- a structural ``Protocol`` naming the capability ("something you can chat
   with"). The web BFF is typed against this abstraction, never against the HTTP client below.

2. ``AiRpcClient`` -- the concrete implementation that POSTs to the ai service's ``chat`` RPC
   tool and validates the reply back into the shared ``ChatOut`` model.

Dependency inversion again: ``deps.py`` injects a real ``AiRpcClient`` at runtime and a fake at
test time; both satisfy ``AiSource`` structurally, so the BFF's code and types are identical
either way. And as always the underlying ``ServiceClient`` owns the injected base_url / token /
transport and converts unreachable-backend transport errors into ``ServiceError`` (an
``RPCError``), which is what lets the BFF degrade gracefully instead of returning a 500 when the
ai service is down.
"""

from typing import Protocol

from rpc.base import ServiceClient

from .contracts import ChatOut


class AiSource(Protocol):
    """The capability contract for chatting with the ai service -- the caller's abstraction.

    A ``typing.Protocol``: any object exposing a matching ``chat`` method satisfies it
    structurally, so the real HTTP client and test fakes are interchangeable with no shared base
    class. The single method mirrors the ai service's single ``chat`` RPC tool.
    """

    # ``...`` is a Protocol stub -- signature/return type only, no implementation.
    def chat(self, message: str) -> ChatOut: ...


class AiRpcClient:
    """Concrete ``AiSource`` that reaches the ai service over RPC.

    Thin by design: it wraps an injected ``ServiceClient`` and maps the one ``chat`` capability
    onto the remote ``chat`` tool, hydrating the JSON response into a typed ``ChatOut``.
    """

    def __init__(self, client: ServiceClient):
        # Keep the injected transport rather than building our own -- base_url/token/transport
        # (and a MockTransport in the in-process e2e tests) are all chosen by deps.py. DI at the
        # wire level, identical to ContentRpcClient.
        self._c = client

    def chat(self, message):
        # POST /rpc/chat with the user's message; the ai service runs its agentic tool-use loop
        # server-side (calling content's tools to ground the answer) and returns the final reply.
        # We validate that JSON back into ChatOut so the caller receives a typed result.
        return ChatOut.model_validate(self._c.call("chat", message=message))
