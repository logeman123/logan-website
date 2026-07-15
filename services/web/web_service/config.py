"""Typed configuration for the web BFF, loaded from the environment.

This module centralizes every value the web service needs to reach its two
back-ends. Crucially, the addresses of those back-ends are *configuration*, not
hard-coded constants — this is dependency injection pushed all the way out to the
network boundary. In local dev the defaults below point at localhost; in
production (e.g. Vercel / docker-compose) the same code picks up different URLs
purely from environment variables, with no code change.

``deps.py`` reads these settings and uses them to construct the concrete RPC
clients, so this file is the single source of truth for "where do the other
services live" and "what token do we present to them".
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the web service.

    Subclassing pydantic-settings' ``BaseSettings`` means every attribute below
    is automatically populated from (in order of precedence) a real environment
    variable of the same name, then the ``.env`` file, then the default literal
    written here. So ``CONTENT_URL=...`` in the deployment environment overrides
    ``content_url`` without touching this file.
    """

    # Shared secret the web service presents as a bearer token on every RPC call
    # to content/ai. The receiving services validate it; "dev-token" is a safe
    # default for offline local dev only and is expected to be overridden in prod.
    service_token: str = "dev-token"
    # Base URL of the content service. Injected into a ServiceClient in deps.py —
    # nothing here bakes the host into the RPC layer.
    content_url: str = "http://localhost:8001"
    # Base URL of the ai service, injected the same way as content_url above.
    ai_url: str = "http://localhost:8002"
    # Load a local ".env" file when present; ``extra="ignore"`` means unrelated
    # environment variables (there are many in any real shell) are silently
    # skipped instead of raising a validation error.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
