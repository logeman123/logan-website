"""Dependency-injection wiring — the ONE place concrete clients are named.

This is the single most important file for understanding the architecture. The
route handlers never import ``ContentRpcClient`` or ``AiRpcClient`` directly;
they depend only on the *Protocols* ``ContentSource`` / ``AiSource`` (structural
interfaces) and let FastAPI's ``Depends(...)`` hand them a concrete object. This
module is where those abstract Protocols get bound to concrete implementations.

Why do it this way (dependency inversion)?
    - Routes stay ignorant of HTTP, tokens, and hostnames — they just call
      ``content.list_projects()`` or ``ai.chat(...)`` against an interface.
    - Tests can override ``get_content`` / ``get_ai`` with in-memory fakes that
      satisfy the same Protocol, so unit tests need no network at all.
    - Swapping transport (e.g. the in-process ``MockTransport`` bridge used by
      the e2e suite) happens by rebuilding the ``ServiceClient`` here, not by
      editing any route.

The layering below is deliberate:
    ServiceClient  -> thin, host-agnostic httpx wrapper (base_url + token +
                      transport all injected); turns unreachable backends into
                      RPCError so callers' "except RPCError" fallbacks fire.
    ContentRpcClient / AiRpcClient
                   -> typed clients that wrap a ServiceClient and expose the
                      RPC tools as ordinary methods, structurally implementing
                      the ContentSource / AiSource Protocols.
"""

from functools import lru_cache

from rpc.ai_rpc.client import AiRpcClient, AiSource
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient, ContentSource

from .config import Settings


@lru_cache
def get_settings():
    """Build (once) and return the environment-driven Settings object.

    ``@lru_cache`` makes this a lazily-initialized singleton: the first call
    constructs ``Settings()`` (which reads env vars / ``.env``) and every later
    call returns the identical cached instance. That means the environment is
    parsed exactly once per process, and the clients built below all share the
    same configuration.
    """
    return Settings()


@lru_cache
def get_content() -> ContentSource:
    """Provide the client the web service uses to reach the content service.

    Declared as returning the ``ContentSource`` *Protocol*, not the concrete
    class — callers depend on the interface, this factory chooses the
    implementation. That is dependency inversion in one line of type annotation.

    Construction reads like the DI story top to bottom:
      1. Pull shared settings (host URL + shared token).
      2. Build a ``ServiceClient`` with the content service's ``base_url`` and a
         ``static_token_provider`` — the token/transport are *injected*, nothing
         about the content host is baked into the RPC library.
      3. Wrap that low-level client in a ``ContentRpcClient`` so routes get typed
         methods (``list_projects`` / ``get_project``) instead of raw RPC calls.

    ``@lru_cache`` again yields a process-wide singleton, so the underlying httpx
    connection pool and cached bearer token are reused across requests.
    """
    s = get_settings()
    return ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))


@lru_cache
def get_ai() -> AiSource:
    """Provide the client the web service uses to reach the ai service.

    Mirror image of ``get_content`` above, pointed at the ai service's URL and
    returning the ``AiSource`` Protocol. When a route calls ``ai.chat(...)``, the
    request travels to the ai service, whose own agentic loop may in turn call
    back into the content service's RPC tools to ground its answer — so a single
    ``/chat`` POST can fan out web -> ai -> content. See ``routes/chat.py``.
    """
    s = get_settings()
    return AiRpcClient(ServiceClient(s.ai_url, static_token_provider(s.service_token)))
