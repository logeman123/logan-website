"""Typed configuration for the content service.

Every microservice in this repo reads its configuration through a Pydantic
``BaseSettings`` subclass instead of scattering ``os.getenv`` calls around the
code. The payoff:

  * values are *typed and validated* once, at the edge (a ``Path`` really becomes
    a ``Path``, a token really becomes a ``str``), so the rest of the service can
    trust them;
  * every field can be overridden from an environment variable of the SAME name
    (``SERVICE_TOKEN``, ``DATA_DIR``) or from a ``.env`` file, which is exactly
    how ``docker-compose`` / ``honcho`` / Vercel inject per-environment config
    without code changes;
  * sane defaults let the whole stack boot with zero configuration for local dev.

This module only *describes* configuration. The single instance that the rest of
the service actually uses is created (and cached) in ``deps.py`` — keeping the
"what are the settings" definition separate from the "who owns the one instance"
wiring is part of this codebase's dependency-injection discipline.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All tunables for the content service, resolved from env / .env / defaults.

    Field resolution order (highest priority first): an explicit constructor arg,
    then a matching environment variable, then a value in the ``.env`` file, then
    the default assigned below. Pydantic performs this lookup and type-coercion
    automatically for every annotated attribute.
    """

    # Shared secret this service expects on incoming RPC calls. The RPC router
    # mounted in main.py compares the caller's `Authorization: Bearer <token>`
    # against this value; callers (the web BFF and the ai service) inject the
    # SAME token from their own configs. The "dev-token" default means the stack
    # authenticates out-of-the-box locally; production overrides SERVICE_TOKEN.
    service_token: str = "dev-token"
    # Filesystem directory the FileContentRepository scans for `*.md` project
    # files. Defaults to the package-local `data/projects/` folder so the service
    # runs with no setup; DATA_DIR can repoint it (e.g. a mounted volume in
    # Docker). Typed as `Path`, so Pydantic coerces any string override for us.
    data_dir: Path = Path(__file__).parent / "data" / "projects"
    # Pydantic-settings behavior: also read from a `.env` file, and silently
    # ignore any unrelated keys in the environment/.env (`extra="ignore"`) so
    # one shared .env across all three services doesn't blow up this service.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
