"""Composition root (dependency injection) for the ai service.

This is the ONE place where abstract Protocols are bound to CONCRETE implementations. Every
other module in this service depends only on interfaces (``LLMProvider``, ``ContentSource``);
here we decide *which* concretes to construct and wire them together. Keeping that decision
in a single file is the whole point of dependency inversion — swap a line here and the rest
of the service is unaffected, which is exactly what makes the code testable and offline-able.

What gets wired:
* ``get_settings`` — loads configuration once (cached).
* ``_build_llm``   — picks the LLM backend (fake vs. real Anthropic) from config.
* ``get_chat``     — builds the RPC client to the content service, then the Chat that
                     combines the chosen LLM with that content source.

main.py calls ``get_chat()`` / ``get_settings()`` at startup to assemble the app.
"""

from functools import lru_cache

# ServiceClient is the shared, transport-agnostic HTTP+JSON RPC client. static_token_provider
# wraps a fixed bearer token as the "token provider" callable the client expects — the token
# is INJECTED, not baked into the client, which is DI at the wire level.
from rpc.base import ServiceClient, static_token_provider
# The typed client for the content service. It wraps a ServiceClient and structurally
# implements the ContentSource Protocol that tools.py/chat.py depend on.
from rpc.content_rpc.client import ContentRpcClient

from .chat import Chat
from .config import Settings
from .llm import AnthropicProvider, FakeLLMProvider, LLMTurn


@lru_cache
def get_settings():
    # @lru_cache makes this a lazy singleton: Settings() (which reads env / .env) runs once,
    # and every caller shares the same instance. Cheap, and ensures consistent config.
    return Settings()


def _build_llm(s):
    # The provider-selection switch. This is where config.llm_provider decides which concrete
    # LLMProvider the Chat will use — the single seam that makes the model swappable.
    if s.llm_provider == "anthropic":
        # Real Claude. Note ``s.llm_base_url or None``: an empty string (the default) becomes
        # None so the SDK uses Anthropic's default host; a non-empty value routes through the
        # Vercel AI Gateway. That's the base_url injection point in action.
        return AnthropicProvider(api_key=s.llm_api_key, base_url=s.llm_base_url or None, model=s.llm_model)
    # Default / offline path: a deterministic fake scripted with a single friendly greeting
    # turn. stop_reason "end_turn" means it answers immediately without requesting tools, so
    # the stack is fully usable with no API key and no network.
    return FakeLLMProvider([LLMTurn("end_turn", text="Hi! Ask me about Logan's projects and work.")])


@lru_cache
def get_chat():
    # Also cached: build the Chat once and reuse it for the app's lifetime.
    s = get_settings()
    # Construct the content client by injecting the base URL and a token provider into a
    # ServiceClient, then wrapping it in the typed ContentRpcClient. This is the concrete
    # ``ContentSource`` that grounds every tool call — but Chat only sees the Protocol.
    content = ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))
    # Finally, combine the chosen LLM and the content source into the Chat that runs the
    # agentic loop. Both are Protocol-typed, so this line is the moment abstraction meets
    # concretion.
    return Chat(llm=_build_llm(s), content=content)
