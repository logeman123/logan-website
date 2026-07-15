# logan-website

Personal site rebuilt as a small monorepo of three FastAPI services that talk over
HTTP+JSON RPC: `web` (HTMX BFF), `content` (owns data), `ai` (Claude-backed chat).

## Local dev (no Docker)

```bash
uv sync
cp .env.example .env
uv run honcho -f Procfile.dev start
```

Then open http://localhost:8000

## Tests

```bash
uv run pytest
```
