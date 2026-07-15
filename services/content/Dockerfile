# =============================================================================
# services/content/Dockerfile  (image for the CONTENT microservice)
# =============================================================================
# All three service Dockerfiles follow the same pattern; only the --package
# name, EXPOSE-d port, and the module in CMD differ. The subtlety of a uv
# WORKSPACE monorepo is that a single service cannot be built in isolation: it
# depends on the local `rpc` member, so the build context (set to the repo root
# in docker-compose) must contain the WHOLE workspace for uv to resolve it.

# Small official Python base image (Debian slim) to keep the image lean.
FROM python:3.12-slim
# Copy the `uv` binary straight out of Astral's published image instead of
# pip-installing it — fast and version-pinned via the tag.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Copy the ENTIRE workspace (root pyproject + rpc/ + all services). This is what
# lets `uv sync` resolve the in-repo `rpc` dependency; copying only this one
# service's folder would break workspace resolution. (.dockerignore trims junk
# like .venv/.git/__pycache__ so they don't bloat the image or the context.)
COPY . /app
# Install ONLY this service's dependency subgraph (`--package content-service`)
# and skip the dev group (`--no-dev` drops pytest/ruff/honcho — not needed at
# runtime). uv creates the shared .venv from the committed uv.lock.
RUN uv sync --package content-service --no-dev
# Documents the port the app listens on (content = 8001). See docker-compose /
# .env.example for how the other services address it.
EXPOSE 8001
# Launch uvicorn (the ASGI server) against this service's FastAPI `app`.
# `--package content-service` runs inside that member's environment; binding to
# 0.0.0.0 (not localhost) is required so the port is reachable from OUTSIDE the
# container (i.e. by the other containers / the host).
CMD ["uv", "run", "--package", "content-service", "uvicorn", "content_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
