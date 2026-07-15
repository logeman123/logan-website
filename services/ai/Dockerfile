# =============================================================================
# services/ai/Dockerfile  (image for the AI / chat microservice)
# =============================================================================
# Same workspace-aware build pattern as the content Dockerfile (see it for the
# detailed rationale). The ai service additionally needs to reach content at
# runtime (CONTENT_URL) for its tool-use loop, but that's a network concern
# wired by docker-compose, not something baked into the image.

# Slim Python base image.
FROM python:3.12-slim
# Pull the uv binary from Astral's published image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Copy the whole workspace so uv can resolve the local `rpc` dependency.
COPY . /app
# Install just the ai-service subgraph (includes the `anthropic` SDK), no dev
# tooling. LLM_PROVIDER defaults to "fake", so the image runs with no API key.
RUN uv sync --package ai-service --no-dev
# ai service listens on 8002.
EXPOSE 8002
# Serve the ai FastAPI app; 0.0.0.0 so it's reachable across the Docker network.
CMD ["uv", "run", "--package", "ai-service", "uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
