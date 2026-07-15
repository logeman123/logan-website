FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY . /app
RUN uv sync --package web-service --no-dev
EXPOSE 8000
CMD ["uv", "run", "--package", "web-service", "uvicorn", "web_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
