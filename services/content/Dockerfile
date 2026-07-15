FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY . /app
RUN uv sync --package content-service --no-dev
EXPOSE 8001
CMD ["uv", "run", "--package", "content-service", "uvicorn", "content_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
