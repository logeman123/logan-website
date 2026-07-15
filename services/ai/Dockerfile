FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY . /app
RUN uv sync --package ai-service --no-dev
EXPOSE 8002
CMD ["uv", "run", "--package", "ai-service", "uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
