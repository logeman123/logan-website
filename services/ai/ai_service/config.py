"""Environment-driven configuration for the **ai** service.

This module centralizes every knob the ai service needs so that nothing downstream has
to read environment variables or hard-code hosts/keys. Using ``pydantic-settings`` means
each field is:

* typed and validated,
* overridable by an environment variable of the same (upper- or lower-case) name,
* overridable by a line in a local ``.env`` file, and
* given a *safe default* so the whole stack boots with ZERO configuration.

That last point is the key design choice for a learning/offline-friendly repo: by
defaulting ``llm_provider`` to ``"fake"``, ``uv run`` / ``honcho start`` brings the AI
service up with no Anthropic API key at all (see ``deps._build_llm``). You opt into the
real Claude model only by setting ``LLM_PROVIDER=anthropic`` plus a key.

Consumers: ``deps.get_settings()`` builds exactly one cached ``Settings`` instance and
hands its fields to the objects that need them — the content service URL and service
token go to the RPC ``ServiceClient``; the LLM fields choose and configure the provider.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Shared bearer token for service-to-service auth. The SAME value must be configured
    # on the content service (it validates it) and here (we send it on outbound calls).
    # "dev-token" is a throwaway default so local dev works without secrets management.
    service_token: str = "dev-token"
    # Base URL of the content service. Injected into the RPC ServiceClient in deps.py —
    # note the host is NOT baked into the client class, it is configuration, which is what
    # lets tests point the client at an in-process app instead of a real socket.
    content_url: str = "http://localhost:8001"
    # Selects which LLMProvider implementation deps.py constructs:
    #   "fake"      -> FakeLLMProvider (deterministic, offline, the default)
    #   "anthropic" -> AnthropicProvider (real Claude API calls)
    llm_provider: str = "fake"          # "anthropic" | "fake"
    # Anthropic API key. Empty by default; only needed when llm_provider == "anthropic".
    llm_api_key: str = ""
    # Optional override for the Anthropic SDK's base URL. Set this to route requests
    # through the Vercel AI Gateway (a proxy) instead of Anthropic's public API host.
    # Empty string means "use the SDK default host" (deps.py converts "" -> None).
    llm_base_url: str = ""              # e.g. the Vercel AI Gateway endpoint
    # Which Claude model the AnthropicProvider should ask for. A small/cheap model is a
    # sensible default for a personal-site chatbot.
    llm_model: str = "claude-haiku-4-5-20251001"
    # pydantic-settings behavior: read a ".env" file if present, and silently ignore any
    # unknown env vars (so unrelated vars in the shell/.env don't crash startup).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
