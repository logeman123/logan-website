# Personal Website Rebuild — Python + HTMX Microservices

- **Date:** 2026-07-15
- **Status:** Approved (design); pending implementation plan
- **Author:** Logan Schwappach (with Claude)
- **Branch:** `rebuild/python-microservices`

## Context

`logan-website` is currently a minimal Next.js 16 / React site on Vercel (a Swiss-design
scaffold with placeholder projects and an "under construction" page). This project rebuilds
it as a **backend-first, server-rendered Python application**.

The rebuild is deliberately a **learning vehicle**, not a minimal personal site. The explicit
goals:

- Play to strengths as a **backend developer**.
- Explore **HTMX** (server-rendered, HTML-over-the-wire) instead of a React SPA.
- Explore **microservices**, **dependency inversion**, and **RPC** — patterns worth deep
  hands-on understanding and increasingly common in modern web architecture.
- Make the site **AI-facing**, starting small and expanding later.

Honest framing: microservices on a personal site is over-engineering in production terms. It
is justified *here* purely as a hands-on way to learn the patterns. The design is sized to stay
tractable enough to actually finish and run.

### Reference architecture (RPC + DI conventions)

The RPC and dependency-inversion conventions below follow well-established patterns for
service-to-service communication:

- **RPC over plain HTTP + JSON** (not gRPC/protobuf). A service exposes named tools at
  `POST /rpc/<tool>` (and `GET /rpc/` lists them). The client is a thin `httpx` wrapper —
  `client.call("tool", **args)`, with `__getattr__` sugar so `client.tool(...)` works and adding
  a server tool needs no client change.
- **Dependency inversion baked into the client:** it bakes in no host — `base_url`,
  `token_provider`, and `transport` are all injected (tests swap a fake transport). Bearer-token
  auth, cached and refreshed before expiry.
- **Multi-service by design:** an `rpc/` umbrella hosts one typed client package per service. The
  RPC tool surface also doubles as the AI/MCP tool surface.

## Goals

1. A monorepo of independently-runnable Python services that communicate only over RPC.
2. A clean, faithful implementation of the RPC + DI patterns, with typed contracts.
3. Server-rendered UI via HTMX + Alpine (HTML fragments over the wire, minimal JS).
4. A working AI-facing chat that answers questions about Logan, grounded in real data.
5. Runs cleanly via `docker-compose up` locally.

## Non-goals (v1)

- **Resume content** — the current resume is stale/non-technical. It is **deliberately untouched**
  and deferred to a future track. No `get_resume`, no `/resume` route, no `ResumeData` model in v1.
- **Deployment** — v1 target is "runs locally." A multi-service host is a future milestone.
- **Full distributed platform** (message broker, API gateway, per-service DBs, service registry,
  observability stack). Named as a "someday" north star; explicitly out of scope for v1.

## Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| Approach | **Monorepo of real services** | Real network boundaries/auth/independent processes = the actual microservices learning. Chosen over a modular monolith (simulated) and a full distributed platform (too much infra before anything is visible). |
| Framework | **FastAPI** | Async; Pydantic models give typed RPC contracts that make DI and the AI tool surface clean. Chosen over Flask/Django. |
| Services | **3: `web`, `content`, `ai`** | Smallest split that exercises the patterns honestly. |
| RPC | **HTTP + JSON, `POST /rpc/<tool>`** | Simple, language-agnostic, doubles as the AI/MCP tool surface. |
| Contracts | **Typed (Pydantic), in the `*_rpc` package** | See below. |
| Packaging | **`uv` per service** | Fast, modern; fits the "modernize the repo" goal. |
| Local dev | **`docker-compose`** | Runs all three services + asset build. |
| Deploy (post-v1) | **EC2 + docker-compose → ECS/Fargate later** | Free `t4g.small` through 2026, 1:1 with local dev + server-ops learning; ECS/Fargate as a later cluster phase. LLM via Vercel AI Gateway. |

### Typed vs. untyped contracts (recorded rationale)

A common RPC-client convention is to stay untyped (dict-in / dict-out). That trade-off is correct
at scale, for reasons worth recording:

- **Independent deployability** — an untyped client depends on nothing but `httpx`, so services
  evolve and deploy without lockstep client rebuilds.
- **Tolerant reader** — reading only needed keys tolerates servers adding fields / rolling out
  new versions gradually; strict client validation would reject newer-but-valid responses.
- **One source of truth on the server**; `__getattr__` sugar means adding a server tool needs
  zero client change.
- The surface is JSON anyway (it doubles as the AI/MCP tool surface).

Every one of those benefits pays off across **org boundaries** (many teams, independent deploys,
uncoordinated version skew). This repo is **single-owner, single-repo, deployed together**, so
that coupling cost is ~zero — and typed contracts buy type safety, autocomplete, refactor
confidence, and dev-time mismatch detection, which is what a "strict repo" should want.

**Decision: typed contracts.** Contracts live in the `*_rpc` package as a shared schema/IDL
layer; both the service and its callers import *that*. No service imports another service. The
only shared-fate cost is a repo-wide Pydantic version bump — trivial for one owner.

## Topology

Three services, one repo. Each is an independently-runnable FastAPI app; they communicate only
over RPC, never by importing each other's internals.

| Service | Owns | Talks to | Public |
|---|---|---|---|
| **`web`** (BFF) | Nothing — pure orchestration; serves HTMX/Jinja pages | `content`, `ai` via RPC | Yes (only browser-facing service) |
| **`content`** | Projects, case studies (data) | — | No (internal) |
| **`ai`** | Claude-backed chat + AI tool surface | `content` via RPC | No (internal) |

**Request flow:** `browser → web (renders HTMX) → RPC → content / ai`. The AI grounds answers by
calling `content` over the *same* RPC surface it uses as tools — the microservices story and the
AI story are one plumbing.

### Repo layout

```
logan-website/
├── services/
│   ├── web/          # FastAPI + Jinja2 + HTMX + Alpine; owns no data
│   │   ├── app/{main.py, routes/, templates/, static/, deps.py}
│   │   ├── frontend/         # SCSS + JS source (built to app/static/)
│   │   └── tests/  Dockerfile  pyproject.toml
│   ├── content/      # owns projects/case studies
│   │   ├── app/{main.py, rpc.py, repository.py, models.py, data/}
│   │   └── tests/  Dockerfile  pyproject.toml
│   └── ai/           # Claude chat + AI/MCP tool surface
│       ├── app/{main.py, rpc.py, chat.py, llm.py, tools.py}
│       └── tests/  Dockerfile  pyproject.toml
├── rpc/              # umbrella of typed clients
│   ├── base.py                # shared httpx client + RPCError hierarchy
│   ├── content_rpc/           # typed methods + Pydantic contracts for content
│   └── ai_rpc/                # typed methods + Pydantic contracts for ai
├── docker-compose.yml         # runs all three locally
├── docs/superpowers/specs/
├── .env.example   README.md
```

## Component: RPC layer & dependency inversion

**Server side (`rpc.py` per service):** a small registry maps a tool name → a handler with a
Pydantic input model. Two endpoints:

- `GET /rpc/` → lists tools (name + schema).
- `POST /rpc/<tool>` → validates the JSON body against the tool's input model, runs the handler,
  returns JSON.

```python
@tool("get_project")                 # registers in the service's tool table
def get_project(args: GetProjectIn) -> ProjectOut:
    return repo.project(args.slug)   # repo is injected
```

**Client side (`rpc/base.py`):** one thin `httpx` wrapper with `call(tool, **args)`, `__getattr__`
sugar, and `error_for_status` → an `RPCError` hierarchy (`InvalidRequest` / `AuthError` /
`NotFound` / `ServiceError`). Injected `base_url`, `token_provider`, `transport`, `timeout`; no
host baked in. Each `content_rpc` / `ai_rpc` package wraps it with typed methods returning
Pydantic models.

**Dependency inversion — two layers:**

1. **Wire level** — `base_url` / `token_provider` / `transport` injected. Tests pass a fake
   `httpx` transport and assert on calls; no network, no running service.
2. **Domain level** — business logic depends on `Protocol` interfaces, not concrete clients or
   SDKs. `web`'s page logic depends on a `ContentSource` protocol; `ai`'s chat depends on
   `LLMProvider` and `ContentSource` protocols. Concrete impls are constructed once per service
   in `deps.py` and injected at startup.

```python
class ContentSource(Protocol):                 # abstraction
    def project(self, slug: str) -> ProjectOut: ...

# web/app/deps.py — the one place concretes are named
content: ContentSource = ContentRpcSource(client=ServiceClient(base_url=settings.CONTENT_URL, ...))
```

**Inter-service auth:** a shared static bearer token from env, returned by a trivial
`token_provider`. It reuses the same seam a real OAuth flow would use, so upgrading later touches
only the wiring.

## Component: `web` (BFF) service

**Stack:** FastAPI + Jinja2 + HTMX + Alpine.js; SCSS/JS compiled from `frontend/` into
`app/static/`. Owns no data — every dynamic value comes from `content` or `ai` over RPC.

**Routes (v1):**

- `/` — home / hero (backend-dev positioning; featured work from `content`).
- `/work` and `/work/{slug}` — project & case-study pages (from `content`).
- `/chat` — the AI-facing page; HTMX posts messages, `web` proxies to `ai`, renders replies.

**HTMX pattern:** pages are server-rendered Jinja. Interactive bits (chat send, filtering work,
expanding a case study) are HTMX partial swaps — `web` handles the request, calls the relevant
service over RPC, and returns an HTML *fragment*. Alpine handles purely-local UI state.

**DI wiring (`app/deps.py`):** the one place concretes are named — builds a `ContentSource`
(via `content_rpc`) and an `AiClient` (via `ai_rpc`) from env config, injected into routes via
FastAPI `Depends`. Routes depend on the protocols, so tests inject fakes and render templates
with no services running.

**Error handling:** if a backend service raises `RPCError`, `web` degrades gracefully — renders
a fallback partial ("work is loading" / "chat temporarily unavailable") rather than 500-ing. As
the only public service, it is the single place user-facing errors are shaped.

## Component: `content` service

**Responsibility:** the single owner of site data (projects, case studies). Exposes it over
`/rpc/` only.

**Storage — `ContentRepository` Protocol + file-backed impl (v1):** content lives as
version-controlled files in `app/data/` — Markdown-with-frontmatter for case-study bodies, YAML
for structured fields. No database in v1 (pure ops overhead for a handful of projects). The
repository is a `Protocol`, so a `SqliteContentRepository` (or Postgres, "per-service DB" style)
is a drop-in later — a clean future DI exercise.

**Contracts (`content_rpc`, shared by server + callers):**

- `ProjectSummary` (slug, title, blurb, tech, year, featured).
- `Project` (adds role, highlights, links, rendered body HTML).

**RPC tools:**

- `list_projects(featured: bool | None)` → `list[ProjectSummary]`.
- `get_project(slug)` → `Project` (raises `NotFound` → RPC 404).

These are also the tools `ai` calls to ground answers — built once, used by both.

**DI / testing:** the repository is injected in `content/app/deps.py`; tests use an in-memory
fake repo seeded with fixtures — no filesystem needed.

## Component: `ai` service

**Responsibility:** the Claude-backed brain. Answers questions about Logan, grounded by calling
`content` over RPC.

**`LLMProvider` Protocol → `AnthropicProvider` impl (DI):** business logic depends on the
abstraction, never the Anthropic SDK directly. Tests inject a fake provider with canned
responses — zero API calls, deterministic. Default model **Claude Haiku 4.5** (cheap/fast),
swappable to Sonnet 5 via config. The provider is pointed at an LLM endpoint via injected base
URL + key — **Vercel AI Gateway** in production (unified key, spend caps, free monthly credits)
or the Anthropic API directly in dev; because it sits behind the abstraction, switching is config,
not code. Build-time detail: routing Claude's tool-use loop through the gateway must use a
tool-calling-capable interface (native Anthropic vs. OpenAI-compatible function-calling) — pinned
when `ai` is built.

**Chat flow (grounded, agentic):**

1. `web` proxies a user message to `ai`'s `chat` tool over RPC.
2. `ai` runs a tool-use loop: Claude decides to call e.g. `get_project("<slug>")` → `ai`
   fulfills it by calling `content` over RPC → feeds results back → Claude answers from real data.
3. `ai` returns the reply; `web` renders it as an HTMX fragment.

The tools Claude can call **are** the `content` RPC tools — "AI-facing" and "microservices RPC"
are the same surface. Expansion point: adding a tool = adding a `content` RPC tool; later, `ai`'s
surface can be exposed as a real **MCP server** (future track) so external AI clients use the
same tools.

**Guardrails:** a system prompt scopes the assistant to "answer questions about Logan," grounding
via tools; basic off-topic / injection guarding. `ANTHROPIC_API_KEY` via env, injected.

**Error handling:** Anthropic failure → `ServiceError` (RPC) → `web` degrades chat gracefully.

## Cross-cutting

- **Config:** each service reads a typed Pydantic `Settings` from env (`CONTENT_URL`, `AI_URL`,
  `SERVICE_TOKEN`, and the LLM endpoint config — `LLM_BASE_URL` + `LLM_API_KEY`, set to the Vercel
  AI Gateway in prod or the Anthropic API in dev); `.env.example` documents them.
- **Testing:** `pytest` per service. DI seams mean unit tests need no network/services; a thin
  set of integration tests run against `docker-compose`.
- **Local dev:** `docker-compose up` runs all three services + rebuilds SCSS/JS. `uv` per service.
- **Deploy:** out of scope for v1 (target = runs locally). See **Deployment plan** below for the
  post-v1 hosting path.

## Deployment plan

**v1 target:** runs locally via `docker-compose up`. Deployment is a follow-on milestone.

**LLM endpoint:** the `ai` service calls **Vercel AI Gateway** (unified key, spend caps, and the
free monthly credits), pointed at Claude Haiku 4.5. This is independent of where the services are
hosted — the gateway works from any host, and the `LLMProvider` abstraction makes it a config swap.

**Hosting (post-v1):** the three services deploy to a single **EC2 instance running the same
`docker-compose.yml`** used locally (`t4g.small`, 2 vCPU / 2 GB — free through Dec 31, 2026 via the
T4g trial, then ~$12/mo). **Caddy** on the box provides auto-HTTPS + reverse-proxy routing to
`web`; `content` and `ai` stay internal (same-host, `localhost`-fast). This keeps a 1:1 local→prod
path and doubles as hands-on server-ops learning.

**Later — cluster-learning phase:** migrate to **ECS/Fargate** to learn real clustering (Cloud Map
service discovery, per-service scaling, ALB). Because RPC authenticates with bearer tokens over
HTTP, the services are **host-agnostic** — this migration is a deploy/config change, not a rewrite.
Progression: local compose → EC2 compose (server ops) → ECS/Fargate (clustering).

## Rollout / migration

- Work happens on branch `rebuild/python-microservices`; `main` (the current Vercel site) stays
  intact until the rebuild is ready to cut over.
- The Next.js app is replaced in this repo (git history preserved). Vercel cannot run the Python
  services, so hosting moves to EC2 (see Deployment plan); Vercel's role narrows to providing the
  AI Gateway. Cut over by repointing DNS once the new stack is ready.

## Content track (separate, user-owned)

Architecture is only as good as what fills it. The real technical content — actual projects,
stack, and professional work — is a **parallel track Logan writes**. The rebuild scaffolds the
structure and a case-study skeleton with clearly-marked placeholders; it invents no facts about
Logan's work. The resume is untouched (see Non-goals).

## Future / open questions

- SQLite (or Postgres per-service DB) drop-in for `content` — a future DI exercise.
- Expose `ai`'s tool surface as a real MCP server.
- Resume + formal experience as a future content + `content`-service track.
- Cut-over execution (DNS repoint) and the later ECS/Fargate cluster migration.
- Expanding the AI-facing feature set.
