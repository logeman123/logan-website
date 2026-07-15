# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo.

## What this is

Logan Schwappach's personal website, deliberately built as a **learning codebase** — a place to
understand how modern backend patterns fit together. It is a monorepo of **three FastAPI
microservices** that talk over **HTTP + JSON RPC**, plus a shared `rpc` library. Backend-first,
with **dependency inversion** throughout. The source files carry verbose educational comments —
read them; they explain the "why."

## ⚠️ Frontend policy — read before touching any UI

**Logan does his own frontend / visual design. Do NOT generate AI frontend, UI, or CSS.**
- Backend / architecture / data / tests: build freely.
- Frontend / visual design: preserve or restore his hand-built UI, or leave it to him. Do not
  create new styled layouts/CSS unless he explicitly asks.
- If a change would remove or replace his frontend, **flag it first**. His original Next.js UI is
  recoverable from git history on `main`.
- The `/resume` page (`templates/resume.html`, `static/resume.css`) is his hand-built "jungle"
  design — don't restyle it without asking. The home page is intentionally a minimal
  under-construction placeholder that he will replace.

## Architecture

Three independently-runnable services communicate only over RPC (never by importing each other):

| Service | Port | Owns | Talks to |
|---|---|---|---|
| `web` (BFF) | 8000 | Nothing — serves HTMX/Jinja pages | `content`, `ai` via RPC |
| `content` | 8001 | Projects/case-study data | — |
| `ai` | 8002 | Claude-backed chat | `content` via RPC |

Request flow: `browser → web (renders HTMX) → RPC → content / ai`. The AI grounds answers by
calling `content` over the **same** RPC surface it uses as tools — the microservices plumbing and
the AI tool surface are one and the same.

## Repo layout

```
rpc/rpc/                     shared library
  exceptions.py              RPCError hierarchy (each has a .status_code)
  base.py                    ServiceClient (injected base_url/token_provider/transport), token cache
  server.py                  ToolRegistry + create_rpc_router (POST /rpc/<tool>, GET /rpc/) + error handler
  content_rpc/, ai_rpc/      typed Pydantic contracts + typed clients (ContentSource/AiSource Protocols)
services/content/content_service/   config, repository (ContentRepository Protocol), tools, deps, main
services/ai/ai_service/             config, llm (LLMProvider Protocol), tools, chat (tool-use loop), rpc_tools, deps, main
services/web/web_service/           config, deps, templating, main, routes/, templates/, static/
tests/e2e/                   in-process full-stack smoke test
docs/superpowers/            the design spec + implementation plan
```

## Run & test

```bash
uv sync
cp .env.example .env
uv run honcho -f Procfile.dev start   # runs all three; open http://localhost:8000
uv run pytest                          # full suite
uv run ruff check rpc services tests   # lint
```

No Docker required for dev or tests. `docker compose up` also works if Docker is installed
(it isn't in the current dev machine, so the compose path is authored but unverified locally).

## Key patterns (the point of the project)

- **RPC:** a service exposes tools at `POST /rpc/<tool>` (JSON body validated against a Pydantic
  input model) and `GET /rpc/` (lists tools). Auth is a bearer token. See `rpc/rpc/server.py`.
- **Dependency inversion:** business logic depends on `Protocol` interfaces, never concretes.
  Wire level — `ServiceClient` takes `base_url` / `token_provider` / `transport` as **injected**
  args (no host baked in), so tests swap a fake transport. Domain level — `web` depends on
  `ContentSource`/`AiSource`, `ai` on `LLMProvider`/`ContentSource`. Each service's `deps.py` is
  the **one place concrete classes are named**.
- **Typed contracts:** live in `rpc/*_rpc/contracts.py` and are the single source of truth,
  imported by both the service and its callers.
- **Errors → HTTP:** `RPCError` subclasses carry a `status_code`; `add_rpc_error_handler` maps them
  (400/401/404/500). `ServiceClient` wraps httpx transport errors as `ServiceError`, so an
  unreachable backend surfaces as an `RPCError` (see graceful degradation).
- **Graceful degradation:** `web` routes catch `RPCError` and render a fallback partial — never 500.
- **Offline by default:** `ai` defaults to `LLMProvider=fake` (a deterministic `FakeLLMProvider`),
  so the whole stack runs with no API key. Real Claude is opt-in via env (see below).
- **Agentic loop:** `ai_service/chat.py` runs a tool-use loop — the model requests a tool, the loop
  executes it by calling `content` over RPC, feeds the result back, and repeats until `end_turn`.

## How to extend

- **New RPC tool on a service:** add its Pydantic in/out models to that service's `*_rpc/contracts.py`,
  register a handler in the service's `tools.py`/`rpc_tools.py` (`@registry.tool("name")` on a
  function taking the input model), and add a typed method to the `*_rpc/client.py` client.
- **New project (content):** drop a Markdown file with YAML frontmatter into
  `services/content/content_service/data/projects/`. No code change — the file-backed repo picks it
  up. Delete `_placeholder.md` when adding real content.
- **New web route:** add a module under `services/web/web_service/routes/`, follow the existing
  pattern (`APIRouter`, `Depends(get_content/get_ai)` for data, catch `RPCError`), and register it
  in `web_service/main.py`.

## Testing conventions

- `pytest`; `testpaths` are configured in the root `pyproject.toml`.
- DI seams mean unit tests need **no network**: `ServiceClient` tests use `httpx.MockTransport`;
  app tests use FastAPI `TestClient` + `dependency_overrides` to inject fakes.
- Test file basenames must be **unique across the repo** (default pytest import mode).
- `tests/e2e/test_stack.py` wires the **real** apps together in-process via an
  `httpx.MockTransport → TestClient` bridge — no network/Docker/API key. Read it to see the whole
  system work end-to-end.

## Conventions & workflow

- **Commits:** casual, lowercase, no `feat:`/`fix:` prefixes; no Claude co-author trailer.
- **`main` is protected** (force-push + deletion blocked; repo admin can bypass). Work on branches
  and open PRs.
- Design spec and implementation plan live in `docs/superpowers/`.
- Open work is tracked as GitHub issues under the **v2** milestone.

## Deploy (future milestone)

Target: a single EC2 instance running the existing `docker-compose.yml`, with **Caddy** for
auto-HTTPS in front of `web`; `content`/`ai` stay internal. LLM calls go through the **Vercel AI
Gateway** (set `LLM_BASE_URL` + `LLM_API_KEY`, `LLM_PROVIDER=anthropic`). ECS/Fargate is a later
"real cluster" exploration. `main` stays on the current Vercel deploy until cutover.

## Environment variables

Per-service, read via pydantic-settings (documented in `.env.example`):
`SERVICE_TOKEN`, `CONTENT_URL`, `AI_URL`, `LLM_PROVIDER` (`fake`|`anthropic`), `LLM_API_KEY`,
`LLM_BASE_URL`, `LLM_MODEL`, `DATA_DIR`.
