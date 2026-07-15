# =============================================================================
# services/web/Dockerfile  (image for the WEB service / BFF)
# =============================================================================
# Same workspace-aware build pattern as the other two Dockerfiles (see the
# content one for the detailed rationale). web is the only service published to
# the host (port 8000); it orchestrates content + ai over RPC at runtime.

# Slim Python base image.
FROM python:3.12-slim
# Pull the uv binary from Astral's published image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Copy the whole workspace so uv can resolve the local `rpc` dependency.
COPY . /app
# Install just the web-service subgraph (fastapi + jinja2 + multipart + rpc),
# skipping dev tooling.
RUN uv sync --package web-service --no-dev
# web service listens on 8000 — the public entrypoint to the site.
EXPOSE 8000
# Serve the web FastAPI app; 0.0.0.0 so the mapped host port can reach it.
CMD ["uv", "run", "--package", "web-service", "uvicorn", "web_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
