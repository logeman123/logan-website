# Python + HTMX Microservices Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the personal site as a monorepo of three FastAPI services (`web`, `content`, `ai`) that talk over HTTP+JSON RPC, with dependency inversion throughout and an AI-facing chat grounded in real content.

**Architecture:** A `uv` workspace holds a shared `rpc` library (thin httpx client + a server-side tool registry + typed per-service contracts) and three service packages. `web` is a browser-facing BFF (FastAPI + Jinja2 + HTMX) that owns no data and orchestrates `content` and `ai` over RPC. `content` owns projects via a file-backed repository behind a `Protocol`. `ai` runs a Claude tool-use loop behind an `LLMProvider` `Protocol`, calling `content` over RPC to ground answers. Every cross-boundary dependency is injected, so tests run with fakes and zero network.

**Tech Stack:** Python 3.12, `uv` (workspace), FastAPI, Uvicorn, httpx, Pydantic v2 + pydantic-settings, Jinja2, HTMX + Alpine.js, python-frontmatter + markdown, `anthropic` SDK (pointed at Vercel AI Gateway in prod), pytest, honcho (local process runner), Docker + docker-compose (optional/additive).

**Commit policy (Logan):** No per-task commits. Tasks are commit-sized and grouped into 5 batches (B1–B5). At each batch boundary the executor stops and asks Logan to commit, with a suggested casual message. Never stage files under `docs/superpowers/`.

**Prerequisites:** `uv` (installed). For Batch B5's container path only: Docker (`brew install colima docker docker-compose && colima start`, or Docker Desktop). No Docker is needed for Batches B1–B4 or the end-to-end test.

---

## Target file structure

```
logan-website/
├── pyproject.toml                      # uv workspace root + dev deps (pytest, honcho, ruff)
├── .python-version                     # 3.12
├── Procfile.dev                        # honcho: runs web/content/ai locally (no Docker)
├── docker-compose.yml                  # additive container path (Batch B5)
├── .env.example
├── scripts/smoke.sh                    # curl-based smoke check for a running stack
├── rpc/                                # shared library (workspace member, package `rpc`)
│   ├── pyproject.toml
│   └── rpc/
│       ├── __init__.py
│       ├── exceptions.py               # RPCError hierarchy + error_for_status
│       ├── base.py                     # ServiceClient + static_token_provider
│       ├── server.py                   # ToolRegistry + create_rpc_router + error handler
│       ├── content_rpc/{__init__,contracts,client}.py
│       └── ai_rpc/{__init__,contracts,client}.py
├── services/
│   ├── content/
│   │   ├── pyproject.toml  Dockerfile
│   │   ├── content_service/{__init__,config,repository,tools,deps,main}.py
│   │   ├── content_service/data/projects/*.md
│   │   └── tests/
│   ├── ai/
│   │   ├── pyproject.toml  Dockerfile
│   │   ├── ai_service/{__init__,config,llm,tools,chat,rpc_tools,deps,main}.py
│   │   └── tests/
│   └── web/
│       ├── pyproject.toml  Dockerfile
│       ├── web_service/{__init__,config,deps,templating,main}.py
│       ├── web_service/routes/{__init__,home,work,chat}.py
│       ├── web_service/templates/*.html
│       ├── web_service/static/{styles.css,htmx.min.js,alpine.min.js}
│       └── tests/
└── tests/e2e/test_stack.py             # in-process full-stack smoke (Batch B5)
```

**Naming invariants (used across tasks):**
- Package names are unique per service (`content_service`, `ai_service`, `web_service`) so they coexist in one workspace venv.
- Ports: `web` 8000 (public), `content` 8001, `ai` 8002.
- Env vars: `SERVICE_TOKEN`, `CONTENT_URL`, `AI_URL`, `LLM_PROVIDER` (`fake`|`anthropic`), `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `DATA_DIR`.
- Contract types live in `rpc/*_rpc/contracts.py` and are imported by both the service and its callers.

---

# Batch B1 — Foundation (scaffold + shared RPC)

### Task 1: Repo scaffold & tooling

**Goal:** Replace the Next.js scaffold with a `uv` workspace whose three (empty-but-importable) service packages and shared `rpc` package install and run under Python 3.12.

**Files:**
- Delete: `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `next.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `eslint.config.mjs`, `src/`, `public/`
- Create: `pyproject.toml`, `.python-version`, `Procfile.dev`, `.env.example`, `rpc/pyproject.toml`, `rpc/rpc/__init__.py`, `services/{content,ai,web}/pyproject.toml`, `services/content/content_service/__init__.py`, `services/ai/ai_service/__init__.py`, `services/web/web_service/__init__.py`
- Modify: `.gitignore`, `README.md`

**Acceptance Criteria:**
- [ ] `uv sync` resolves the workspace and creates `.venv` on Python 3.12
- [ ] `uv run python -c "import rpc, content_service, ai_service, web_service"` prints nothing and exits 0
- [ ] `.gitignore` ignores Python artifacts (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`)
- [ ] Next.js files are gone from `git status`

**Verify:** `uv sync && uv run python -c "import rpc, content_service, ai_service, web_service; print('ok')"` → prints `ok`

**Steps:**

- [ ] **Step 1: Remove the Next.js scaffold** (preserved in git history + on `main`)

Run:
```bash
git rm -r --quiet src public
git rm --quiet package.json package-lock.json pnpm-lock.yaml next.config.ts tsconfig.json tailwind.config.ts postcss.config.js eslint.config.mjs
```

- [ ] **Step 2: Pin Python**

Create `.python-version`:
```
3.12
```

- [ ] **Step 3: Workspace root `pyproject.toml`**

```toml
[project]
name = "logan-website"
version = "0.1.0"
description = "Personal site — Python + HTMX microservices"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["rpc", "services/*"]

[tool.uv]
package = false

[tool.uv.sources]
rpc = { workspace = true }
content-service = { workspace = true }
ai-service = { workspace = true }
web-service = { workspace = true }

[dependency-groups]
dev = ["pytest>=8", "httpx>=0.27", "honcho>=2", "ruff>=0.6"]
```

- [ ] **Step 4: Shared `rpc` library package**

Create `rpc/pyproject.toml`:
```toml
[project]
name = "rpc"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "pydantic>=2.7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["rpc"]
```

Create `rpc/rpc/__init__.py`:
```python
"""Shared RPC layer: thin client, server-side tool registry, typed contracts."""
```

- [ ] **Step 5: Three service packages**

Create `services/content/pyproject.toml`:
```toml
[project]
name = "content-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic-settings>=2.3",
    "python-frontmatter>=1.1", "markdown>=3.6", "rpc",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["content_service"]
```

Create `services/ai/pyproject.toml`:
```toml
[project]
name = "ai-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic-settings>=2.3",
    "anthropic>=0.40", "rpc",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["ai_service"]
```

Create `services/web/pyproject.toml`:
```toml
[project]
name = "web-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic-settings>=2.3",
    "jinja2>=3.1", "python-multipart>=0.0.9", "rpc",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["web_service"]
```

Create the three package inits (empty is fine):
- `services/content/content_service/__init__.py`
- `services/ai/ai_service/__init__.py`
- `services/web/web_service/__init__.py`

- [ ] **Step 6: `Procfile.dev` and `.env.example`**

`Procfile.dev`:
```
content: uv run uvicorn content_service.main:app --port 8001 --reload
ai: uv run uvicorn ai_service.main:app --port 8002 --reload
web: uv run uvicorn web_service.main:app --port 8000 --reload
```

`.env.example`:
```
SERVICE_TOKEN=dev-token
CONTENT_URL=http://localhost:8001
AI_URL=http://localhost:8002
LLM_PROVIDER=fake
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=claude-haiku-4-5-20251001
```

- [ ] **Step 7: Update `.gitignore`**

Append:
```
# python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 8: Rewrite `README.md`** (short, honest)

```markdown
# logan-website

Personal site rebuilt as a small monorepo of three FastAPI services that talk over
HTTP+JSON RPC: `web` (HTMX BFF), `content` (owns data), `ai` (Claude-backed chat).

## Local dev (no Docker)
    uv sync
    cp .env.example .env
    uv run honcho -f Procfile.dev start
Then open http://localhost:8000

## Tests
    uv run pytest
```

- [ ] **Step 9: Verify**

Run: `uv sync && uv run python -c "import rpc, content_service, ai_service, web_service; print('ok')"`
Expected: `ok` (and `.venv` created on 3.12)

- [ ] **Step 10: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 2: Shared RPC layer (exceptions, client, server registry)

**Goal:** Implement the reusable RPC building blocks — the `RPCError` hierarchy, the injectable `ServiceClient`, and a server-side `ToolRegistry` + FastAPI router — all unit-tested with a fake httpx transport (no network).

**Files:**
- Create: `rpc/rpc/exceptions.py`, `rpc/rpc/base.py`, `rpc/rpc/server.py`
- Test: `rpc/tests/test_client.py`, `rpc/tests/test_server.py`

**Acceptance Criteria:**
- [ ] `ServiceClient.call(tool, **args)` sends a bearer token and returns parsed JSON; `client.foo(**args)` sugar works
- [ ] Non-2xx responses raise the mapped `RPCError` subclass
- [ ] Token is cached across calls and only re-fetched after expiry
- [ ] `ToolRegistry` validates input against the handler's Pydantic model; unknown tool → `NotFound`, bad body → `InvalidRequest`
- [ ] The router enforces the bearer token (401 on mismatch) and exposes `GET /rpc/` + `POST /rpc/{tool}`

**Verify:** `uv run pytest rpc/tests -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing client + server tests**

`rpc/tests/test_client.py`:
```python
import json
import httpx
import pytest
from rpc.base import ServiceClient, static_token_provider
from rpc.exceptions import NotFound, AuthError


def _client(handler, token="t"):
    return ServiceClient("http://svc", static_token_provider(token),
                         transport=httpx.MockTransport(handler))


def test_call_sends_bearer_and_returns_json():
    def handler(request):
        assert request.headers["authorization"] == "Bearer t"
        assert json.loads(request.content) == {"slug": "x"}
        assert request.url.path == "/rpc/get_project"
        return httpx.Response(200, json={"slug": "x", "ok": True})
    assert _client(handler).get_project(slug="x") == {"slug": "x", "ok": True}


def test_error_status_maps_to_exception():
    def handler(request):
        return httpx.Response(404, text="nope")
    with pytest.raises(NotFound):
        _client(handler).get_project(slug="missing")


def test_token_is_cached():
    calls = {"n": 0}
    def provider():
        calls["n"] += 1
        return "tok", 3600.0
    def handler(request):
        return httpx.Response(200, json={})
    c = ServiceClient("http://svc", provider, transport=httpx.MockTransport(handler))
    c.call("a"); c.call("b")
    assert calls["n"] == 1
```

`rpc/tests/test_server.py`:
```python
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from rpc.server import ToolRegistry, create_rpc_router, add_rpc_error_handler
from rpc.exceptions import NotFound


class EchoIn(BaseModel):
    value: str


def _app(token="t"):
    reg = ToolRegistry()

    @reg.tool("echo")
    def echo(args: EchoIn) -> dict:
        return {"echo": args.value}

    @reg.tool("boom")
    def boom(args: EchoIn) -> dict:
        raise NotFound("gone")

    app = FastAPI()
    add_rpc_error_handler(app)
    app.include_router(create_rpc_router(reg, token))
    return TestClient(app)


def test_dispatch_ok():
    r = _app().post("/rpc/echo", json={"value": "hi"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json() == {"echo": "hi"}


def test_bad_token_is_401():
    r = _app().post("/rpc/echo", json={"value": "hi"}, headers={"Authorization": "Bearer NOPE"})
    assert r.status_code == 401


def test_unknown_tool_is_404():
    r = _app().post("/rpc/nope", json={}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_validation_error_is_400():
    r = _app().post("/rpc/echo", json={"wrong": 1}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 400


def test_handler_rpcerror_maps_status():
    r = _app().post("/rpc/boom", json={"value": "x"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_list_tools():
    r = _app().get("/rpc/", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and "echo" in r.json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest rpc/tests -v`
Expected: FAIL (`ModuleNotFoundError: rpc.exceptions` / `rpc.server`)

- [ ] **Step 3: Implement `rpc/rpc/exceptions.py`**

```python
class RPCError(Exception):
    """Base for all RPC client/server errors."""


class InvalidRequest(RPCError):
    """400 — request rejected (missing/invalid arguments)."""


class AuthError(RPCError):
    """401 — missing or invalid credentials."""


class NotFound(RPCError):
    """404 — referenced entity does not exist."""


class ServiceError(RPCError):
    """5xx — the RPC service failed."""


_BY_STATUS = {400: InvalidRequest, 401: AuthError, 404: NotFound}


def error_for_status(status_code, detail):
    if status_code in _BY_STATUS:
        return _BY_STATUS[status_code](detail)
    if status_code >= 500:
        return ServiceError(detail)
    return RPCError(f"unexpected status {status_code}: {detail}")
```

- [ ] **Step 4: Implement `rpc/rpc/base.py`**

```python
import time

import httpx

from rpc.exceptions import AuthError, RPCError, error_for_status

DEFAULT_TIMEOUT = 30.0
DEFAULT_TOKEN_MARGIN = 60.0


def static_token_provider(token, expires_in=3600.0):
    """A token_provider that always returns the same static bearer token."""
    def provider():
        return token, expires_in
    return provider


class ServiceClient:
    """Thin RPC client. Bakes in no host — base_url, token_provider and transport are injected."""

    def __init__(self, base_url, token_provider, *, transport=None,
                 timeout=DEFAULT_TIMEOUT, token_margin=DEFAULT_TOKEN_MARGIN):
        if not base_url:
            raise ValueError("base_url is required (the RPC target URL)")
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._token_margin = token_margin
        self._cached_token = None
        self._token_expiry = 0.0
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._http.close()

    def _token(self):
        now = time.monotonic()
        if self._cached_token is None or now >= self._token_expiry:
            try:
                token, expires_in = self._token_provider()
            except RPCError:
                raise
            except Exception as exc:
                raise AuthError(f"failed to obtain RPC token: {exc}") from exc
            self._cached_token = token
            self._token_expiry = now + max(0.0, float(expires_in) - self._token_margin)
        return self._cached_token

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}"}

    def call(self, tool, **arguments):
        resp = self._http.post(f"{self._base_url}/rpc/{tool}", headers=self._headers(), json=arguments)
        if resp.is_success:
            return resp.json()
        raise error_for_status(resp.status_code, resp.text)

    def list_tools(self):
        resp = self._http.get(f"{self._base_url}/rpc/", headers=self._headers())
        if resp.is_success:
            return resp.json()
        raise error_for_status(resp.status_code, resp.text)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda **arguments: self.call(name, **arguments)
```

- [ ] **Step 5: Implement `rpc/rpc/server.py`**

```python
from typing import get_type_hints

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from rpc.exceptions import AuthError, InvalidRequest, NotFound, RPCError, ServiceError


class ToolRegistry:
    """Maps tool name -> (handler, pydantic input model). Handlers take one BaseModel arg."""

    def __init__(self):
        self._tools = {}

    def tool(self, name):
        def deco(fn):
            hints = get_type_hints(fn)
            params = [v for k, v in hints.items() if k != "return"]
            if not params or not (isinstance(params[0], type) and issubclass(params[0], BaseModel)):
                raise TypeError(f"tool {name!r} handler must take a pydantic BaseModel arg")
            self._tools[name] = (fn, params[0])
            return fn
        return deco

    def names(self):
        return {name: model.model_json_schema() for name, (fn, model) in self._tools.items()}

    def dispatch(self, name, payload):
        if name not in self._tools:
            raise NotFound(f"unknown tool: {name}")
        fn, model = self._tools[name]
        try:
            args = model.model_validate(payload)
        except ValidationError as exc:
            raise InvalidRequest(str(exc)) from exc
        return _to_jsonable(fn(args))


def _to_jsonable(result):
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_to_jsonable(x) for x in result]
    return result


def create_rpc_router(registry, expected_token):
    router = APIRouter()

    def _check(authorization):
        if authorization != f"Bearer {expected_token}":
            raise AuthError("missing or invalid credentials")

    @router.get("/rpc/")
    def list_tools(authorization: str = Header(default="")):
        _check(authorization)
        return registry.names()

    @router.post("/rpc/{tool}")
    async def call_tool(tool: str, request: Request, authorization: str = Header(default="")):
        _check(authorization)
        body = await request.body()
        payload = await request.json() if body else {}
        try:
            return registry.dispatch(tool, payload)
        except RPCError:
            raise
        except Exception as exc:  # unexpected handler failure -> 500
            raise ServiceError(str(exc)) from exc

    return router


_STATUS = [(InvalidRequest, 400), (AuthError, 401), (NotFound, 404), (ServiceError, 500)]


def add_rpc_error_handler(app):
    @app.exception_handler(RPCError)
    async def _handle(request, exc):
        status = next((s for cls, s in _STATUS if isinstance(exc, cls)), 500)
        return JSONResponse(status_code=status, content={"detail": str(exc)})
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest rpc/tests -v`
Expected: PASS (all client + server tests)

- [ ] **Step 7: End of Batch B1 — DO NOT commit.**

`End of Batch B1.` Suggested commit message for Logan:
```
scaffold python monorepo and shared rpc layer
```

---

# Batch B2 — Content service

### Task 3: Content contracts + repository + sample data

**Goal:** Define the `content` wire contracts (in `content_rpc`) and a `ContentRepository` `Protocol` with a file-backed implementation and an in-memory fake, plus seed one real project (this website).

**Files:**
- Create: `rpc/rpc/content_rpc/__init__.py`, `rpc/rpc/content_rpc/contracts.py`, `services/content/content_service/repository.py`, `services/content/content_service/data/projects/this-website.md`, `services/content/content_service/data/projects/_placeholder.md`
- Test: `services/content/tests/test_repository.py`

**Acceptance Criteria:**
- [ ] `ProjectSummary` and `Project` contracts exist in `content_rpc.contracts`
- [ ] `FileContentRepository` loads `*.md` (YAML frontmatter + markdown body → `body_html`)
- [ ] `list_projects(featured=True)` returns only featured summaries; `project(slug)` raises `NotFound` for a missing slug
- [ ] `InMemoryContentRepository` behaves identically (used by tests)

**Verify:** `uv run pytest services/content/tests/test_repository.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing repository test**

`services/content/tests/test_repository.py`:
```python
import pytest
from rpc.content_rpc.contracts import Project
from rpc.exceptions import NotFound
from content_service.repository import FileContentRepository, InMemoryContentRepository

DATA = __import__("pathlib").Path(__file__).parents[1] / "content_service" / "data" / "projects"


@pytest.fixture(params=["file", "memory"])
def repo(request):
    if request.param == "file":
        return FileContentRepository(DATA)
    projects = FileContentRepository(DATA).list_projects()
    full = [FileContentRepository(DATA).project(p.slug) for p in projects]
    return InMemoryContentRepository(full)


def test_list_all(repo):
    slugs = {p.slug for p in repo.list_projects()}
    assert "this-website" in slugs


def test_featured_filter(repo):
    featured = repo.list_projects(featured=True)
    assert all(p.featured for p in featured)
    assert any(p.slug == "this-website" for p in featured)


def test_get_project_renders_body(repo):
    p = repo.project("this-website")
    assert isinstance(p, Project)
    assert "<" in p.body_html  # markdown rendered to HTML


def test_missing_raises(repo):
    with pytest.raises(NotFound):
        repo.project("does-not-exist")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest services/content/tests/test_repository.py -v`
Expected: FAIL (`ModuleNotFoundError` / missing data files)

- [ ] **Step 3: Implement contracts** `rpc/rpc/content_rpc/__init__.py`

```python
"""content service contracts + typed client (the published RPC surface)."""
```

`rpc/rpc/content_rpc/contracts.py`:
```python
from pydantic import BaseModel


class ProjectSummary(BaseModel):
    slug: str
    title: str
    blurb: str = ""
    tech: list[str] = []
    year: int | None = None
    featured: bool = False


class Project(ProjectSummary):
    role: str = ""
    highlights: list[str] = []
    links: dict[str, str] = {}
    body_html: str = ""


class ListProjectsIn(BaseModel):
    featured: bool | None = None


class GetProjectIn(BaseModel):
    slug: str
```

- [ ] **Step 4: Implement `services/content/content_service/repository.py`**

```python
from pathlib import Path
from typing import Protocol

import frontmatter
import markdown

from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import NotFound


class ContentRepository(Protocol):
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    def project(self, slug: str) -> Project: ...


def _summaries(projects):
    return [ProjectSummary.model_validate(p.model_dump()) for p in projects]


def _filter(projects, featured):
    if featured is None:
        return list(projects)
    return [p for p in projects if p.featured == featured]


class FileContentRepository:
    def __init__(self, data_dir):
        self._dir = Path(data_dir)

    def _load(self):
        out = {}
        for path in sorted(self._dir.glob("*.md")):
            post = frontmatter.load(path)
            meta = post.metadata
            slug = meta.get("slug", path.stem)
            out[slug] = Project(
                slug=slug,
                title=meta.get("title", ""),
                blurb=meta.get("blurb", ""),
                tech=meta.get("tech", []),
                year=meta.get("year"),
                featured=bool(meta.get("featured", False)),
                role=meta.get("role", ""),
                highlights=meta.get("highlights", []),
                links=meta.get("links", {}),
                body_html=markdown.markdown(post.content),
            )
        return out

    def list_projects(self, featured=None):
        return _summaries(_filter(self._load().values(), featured))

    def project(self, slug):
        projects = self._load()
        if slug not in projects:
            raise NotFound(f"no project: {slug}")
        return projects[slug]


class InMemoryContentRepository:
    def __init__(self, projects: list[Project]):
        self._projects = {p.slug: p for p in projects}

    def list_projects(self, featured=None):
        return _summaries(_filter(self._projects.values(), featured))

    def project(self, slug):
        if slug not in self._projects:
            raise NotFound(f"no project: {slug}")
        return self._projects[slug]
```

- [ ] **Step 5: Seed content** `services/content/content_service/data/projects/this-website.md`

```markdown
---
slug: this-website
title: This Website
blurb: A personal site rebuilt as three FastAPI microservices talking over HTTP+JSON RPC.
year: 2026
featured: true
tech: [Python, FastAPI, HTMX, Alpine.js, httpx, Docker]
role: Designer & sole engineer
highlights:
  - Three independently-runnable services (web / content / ai) with a shared typed RPC layer.
  - Dependency inversion throughout — every cross-service call is injected and fakeable in tests.
  - An AI chat whose tool surface is the same RPC surface the services use.
links:
  source: https://github.com/logeman123/logan-website
---
This site is itself the portfolio piece: a from-scratch exploration of microservices,
dependency inversion, and RPC using Python and HTMX. The write-up below walks through the
architecture and the decisions behind it.

## Why microservices for a personal site
Honestly? To learn them well. Read on for how the pieces fit together.
```

`services/content/content_service/data/projects/_placeholder.md` (clearly-marked stub, no invented facts):
```markdown
---
slug: placeholder-project
title: "TODO: Project Title"
blurb: "TODO — replace this file with a real project write-up."
year: 2025
featured: false
tech: []
role: ""
highlights: []
links: {}
---
TODO: Logan to fill in a real project or professional case study here.
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run pytest services/content/tests/test_repository.py -v`
Expected: PASS

- [ ] **Step 7: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 4: Content service app + typed client

**Goal:** Wire the repository into a FastAPI app exposing `list_projects` / `get_project` over `/rpc/`, and add the typed `ContentRpcClient` (implementing a `ContentSource` `Protocol`) that callers use.

**Files:**
- Create: `services/content/content_service/config.py`, `services/content/content_service/tools.py`, `services/content/content_service/deps.py`, `services/content/content_service/main.py`, `rpc/rpc/content_rpc/client.py`
- Test: `services/content/tests/test_app.py`, `rpc/tests/test_content_client.py`

**Acceptance Criteria:**
- [ ] `POST /rpc/get_project {"slug":"this-website"}` (with token) returns the project; missing slug → 404; bad token → 401
- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `ContentRpcClient` returns parsed `ProjectSummary`/`Project` objects and satisfies `ContentSource`

**Verify:** `uv run pytest services/content/tests/test_app.py rpc/tests/test_content_client.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests**

`services/content/tests/test_app.py`:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rpc.content_rpc.contracts import Project
from rpc.server import create_rpc_router, add_rpc_error_handler
from content_service.repository import InMemoryContentRepository
from content_service.tools import build_content_registry

P = Project(slug="a", title="A", blurb="b", featured=True, body_html="<p>x</p>")


def _client():
    app = FastAPI()
    add_rpc_error_handler(app)
    app.include_router(create_rpc_router(build_content_registry(InMemoryContentRepository([P])), "t"))
    return TestClient(app)


def test_get_project_ok():
    r = _client().post("/rpc/get_project", json={"slug": "a"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json()["title"] == "A"


def test_get_project_missing_404():
    r = _client().post("/rpc/get_project", json={"slug": "z"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_list_featured():
    r = _client().post("/rpc/list_projects", json={"featured": True}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and [p["slug"] for p in r.json()] == ["a"]
```

`rpc/tests/test_content_client.py`:
```python
import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient


def test_typed_client_parses_models():
    def handler(request):
        if request.url.path == "/rpc/get_project":
            return httpx.Response(200, json={"slug": "a", "title": "A", "body_html": "<p/>"})
        return httpx.Response(200, json=[{"slug": "a", "title": "A"}])
    c = ContentRpcClient(ServiceClient("http://content", static_token_provider("t"),
                                       transport=httpx.MockTransport(handler)))
    assert c.get_project("a").title == "A"
    assert c.list_projects(featured=True)[0].slug == "a"
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/content/tests/test_app.py rpc/tests/test_content_client.py -v`
Expected: FAIL (missing modules)

- [ ] **Step 3: Implement `config.py`**

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    data_dir: Path = Path(__file__).parent / "data" / "projects"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

- [ ] **Step 4: Implement `tools.py`**

```python
from rpc.content_rpc.contracts import GetProjectIn, ListProjectsIn, Project, ProjectSummary
from rpc.server import ToolRegistry

from .repository import ContentRepository


def build_content_registry(repo: ContentRepository) -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool("list_projects")
    def list_projects(args: ListProjectsIn) -> list[ProjectSummary]:
        return repo.list_projects(featured=args.featured)

    @reg.tool("get_project")
    def get_project(args: GetProjectIn) -> Project:
        return repo.project(args.slug)

    return reg
```

- [ ] **Step 5: Implement `deps.py`**

```python
from functools import lru_cache

from .config import Settings
from .repository import FileContentRepository


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_repository():
    return FileContentRepository(get_settings().data_dir)
```

- [ ] **Step 6: Implement `main.py`**

```python
from fastapi import FastAPI

from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_repository, get_settings
from .tools import build_content_registry

app = FastAPI(title="content")
add_rpc_error_handler(app)
app.include_router(create_rpc_router(build_content_registry(get_repository()), get_settings().service_token))


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Implement `rpc/rpc/content_rpc/client.py`**

```python
from typing import Protocol

from rpc.base import ServiceClient

from .contracts import Project, ProjectSummary


class ContentSource(Protocol):
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    def get_project(self, slug: str) -> Project: ...


class ContentRpcClient:
    def __init__(self, client: ServiceClient):
        self._c = client

    def list_projects(self, featured=None):
        rows = self._c.call("list_projects", featured=featured)
        return [ProjectSummary.model_validate(r) for r in rows]

    def get_project(self, slug):
        return Project.model_validate(self._c.call("get_project", slug=slug))
```

- [ ] **Step 8: Run to verify pass**

Run: `uv run pytest services/content/tests/test_app.py rpc/tests/test_content_client.py -v`
Expected: PASS

- [ ] **Step 9: End of Batch B2 — DO NOT commit.**

`End of Batch B2.` Suggested commit message for Logan:
```
add content service with file-backed repo and typed rpc client
```

---

# Batch B3 — AI service

### Task 5: LLM provider abstraction

**Goal:** Define the `LLMProvider` `Protocol` with a real `AnthropicProvider` (pointable at the Vercel AI Gateway via base_url) and a deterministic `FakeLLMProvider`, plus the `LLMTurn`/`ToolUse` value types.

**Files:**
- Create: `services/ai/ai_service/llm.py`
- Test: `services/ai/tests/test_llm.py`

**Acceptance Criteria:**
- [ ] `LLMTurn` carries `stop_reason`, `text`, and `tool_uses: list[ToolUse]`
- [ ] `FakeLLMProvider` returns scripted turns in order (last turn repeats)
- [ ] `AnthropicProvider` maps Anthropic content blocks → `LLMTurn` (unit-tested with a stub client, no network)

**Verify:** `uv run pytest services/ai/tests/test_llm.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing test**

`services/ai/tests/test_llm.py`:
```python
from types import SimpleNamespace
from ai_service.llm import AnthropicProvider, FakeLLMProvider, LLMTurn, ToolUse


def test_fake_returns_scripted_then_repeats():
    p = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
                         LLMTurn("end_turn", text="done")])
    assert p.run(system="s", messages=[], tools=[]).stop_reason == "tool_use"
    assert p.run(system="s", messages=[], tools=[]).text == "done"
    assert p.run(system="s", messages=[], tools=[]).text == "done"  # repeats last


def test_anthropic_maps_blocks(monkeypatch):
    blocks = [SimpleNamespace(type="text", text="hi"),
              SimpleNamespace(type="tool_use", id="9", name="get_project", input={"slug": "a"})]
    fake_resp = SimpleNamespace(stop_reason="tool_use", content=blocks)

    prov = AnthropicProvider.__new__(AnthropicProvider)   # bypass __init__ (no SDK/network)
    prov._client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_resp))
    prov._model, prov._max_tokens = "m", 100

    turn = prov.run(system="s", messages=[], tools=[])
    assert turn.text == "hi"
    assert turn.tool_uses[0].name == "get_project"
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/ai/tests/test_llm.py -v`
Expected: FAIL (`ModuleNotFoundError: ai_service.llm`)

- [ ] **Step 3: Implement `services/ai/ai_service/llm.py`**

```python
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class LLMTurn:
    stop_reason: str            # "tool_use" | "end_turn" | ...
    text: str = ""
    tool_uses: list[ToolUse] = field(default_factory=list)


class LLMProvider(Protocol):
    def run(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMTurn: ...


class AnthropicProvider:
    def __init__(self, *, api_key, base_url=None, model="claude-haiku-4-5-20251001", max_tokens=1024):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key, base_url=base_url) if base_url else Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def run(self, *, system, messages, tools):
        resp = self._client.messages.create(
            model=self._model, max_tokens=self._max_tokens,
            system=system, messages=messages, tools=tools,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_uses = [ToolUse(id=b.id, name=b.name, input=dict(b.input))
                     for b in resp.content if b.type == "tool_use"]
        return LLMTurn(stop_reason=resp.stop_reason, text=text, tool_uses=tool_uses)


class FakeLLMProvider:
    """Deterministic provider for tests and offline dev — returns scripted turns in order."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = list(turns)
        self._i = 0

    def run(self, *, system, messages, tools):
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return turn
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest services/ai/tests/test_llm.py -v`
Expected: PASS

- [ ] **Step 5: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 6: Chat orchestration + content-backed tools

**Goal:** Implement the agentic tool-use loop (`Chat.reply`) and the content-backed tool executor, depending only on the `LLMProvider` and `ContentSource` abstractions — tested with fakes.

**Files:**
- Create: `services/ai/ai_service/tools.py`, `services/ai/ai_service/chat.py`
- Test: `services/ai/tests/test_chat.py`

**Acceptance Criteria:**
- [ ] `TOOL_SPECS` describes `list_projects` and `get_project` as Anthropic tool schemas
- [ ] `execute_tool` calls the injected `ContentSource` and returns a text summary; RPC failures return a safe error string (loop continues)
- [ ] `Chat.reply` runs the loop: on `tool_use` it executes tools and re-queries; on `end_turn` it returns text; it stops at `max_steps`

**Verify:** `uv run pytest services/ai/tests/test_chat.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing test**

`services/ai/tests/test_chat.py`:
```python
from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn, ToolUse


class FakeContent:
    def list_projects(self, featured=None):
        return [ProjectSummary(slug="a", title="A", blurb="b")]

    def get_project(self, slug):
        return Project(slug=slug, title="A", blurb="b", year=2026, role="dev", tech=["Python"])


class BrokenContent:
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


def test_loop_executes_tool_then_answers():
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="Logan built A."),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("tell me about A") == "Logan built A."


def test_direct_answer_no_tools():
    llm = FakeLLMProvider([LLMTurn("end_turn", text="hi")])
    assert Chat(llm=llm, content=FakeContent()).reply("hello") == "hi"


def test_tool_error_is_survived():
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="couldn't fetch that"),
    ])
    assert Chat(llm=llm, content=BrokenContent()).reply("x") == "couldn't fetch that"


def test_max_steps_guard():
    llm = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "list_projects", {})])])
    out = Chat(llm=llm, content=FakeContent(), max_steps=2).reply("loop")
    assert "couldn't" in out.lower()
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/ai/tests/test_chat.py -v`
Expected: FAIL (missing modules)

- [ ] **Step 3: Implement `services/ai/ai_service/tools.py`**

```python
from rpc.content_rpc.client import ContentSource
from rpc.exceptions import RPCError

TOOL_SPECS = [
    {
        "name": "list_projects",
        "description": "List Logan's projects. Optional boolean 'featured' filter.",
        "input_schema": {
            "type": "object",
            "properties": {"featured": {"type": "boolean"}},
        },
    },
    {
        "name": "get_project",
        "description": "Get one of Logan's projects by its slug.",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
]


def execute_tool(content: ContentSource, name: str, args: dict) -> str:
    try:
        if name == "list_projects":
            rows = content.list_projects(featured=args.get("featured"))
            return "\n".join(f"{p.slug}: {p.title} — {p.blurb}" for p in rows) or "No projects found."
        if name == "get_project":
            p = content.get_project(args["slug"])
            return (f"{p.title} ({p.year})\nRole: {p.role}\nTech: {', '.join(p.tech)}\n"
                    f"{p.blurb}\nHighlights: {'; '.join(p.highlights)}")
        return f"Unknown tool: {name}"
    except RPCError as exc:
        return f"(tool error fetching content: {exc})"
```

- [ ] **Step 4: Implement `services/ai/ai_service/chat.py`**

```python
from rpc.content_rpc.client import ContentSource

from .llm import LLMProvider
from .tools import TOOL_SPECS, execute_tool

SYSTEM = (
    "You are the assistant on Logan Schwappach's personal website. "
    "Answer questions about Logan, his projects, and his work, using the tools to fetch real data "
    "rather than guessing. If asked something unrelated, briefly steer back to Logan's work."
)


class Chat:
    def __init__(self, *, llm: LLMProvider, content: ContentSource, max_steps: int = 5):
        self._llm = llm
        self._content = content
        self._max_steps = max_steps

    def reply(self, message: str) -> str:
        messages = [{"role": "user", "content": message}]
        for _ in range(self._max_steps):
            turn = self._llm.run(system=SYSTEM, messages=messages, tools=TOOL_SPECS)
            if turn.stop_reason != "tool_use":
                return turn.text
            assistant = []
            if turn.text:
                assistant.append({"type": "text", "text": turn.text})
            for tu in turn.tool_uses:
                assistant.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
            messages.append({"role": "assistant", "content": assistant})
            results = [
                {"type": "tool_result", "tool_use_id": tu.id,
                 "content": execute_tool(self._content, tu.name, tu.input)}
                for tu in turn.tool_uses
            ]
            messages.append({"role": "user", "content": results})
        return "Sorry — I couldn't complete that request."
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest services/ai/tests/test_chat.py -v`
Expected: PASS

- [ ] **Step 6: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 7: AI service app + typed client

**Goal:** Expose `Chat` as a `chat` RPC tool, wire config + DI (fake provider by default, Anthropic when configured), and add the typed `AiRpcClient`.

**Files:**
- Create: `services/ai/ai_service/config.py`, `services/ai/ai_service/rpc_tools.py`, `services/ai/ai_service/deps.py`, `services/ai/ai_service/main.py`, `rpc/rpc/ai_rpc/__init__.py`, `rpc/rpc/ai_rpc/contracts.py`, `rpc/rpc/ai_rpc/client.py`
- Test: `services/ai/tests/test_app.py`, `rpc/tests/test_ai_client.py`

**Acceptance Criteria:**
- [ ] `POST /rpc/chat {"message":"hi"}` (with token) returns `{"reply": "..."}`; `GET /health` ok
- [ ] With `LLM_PROVIDER=fake` (default) the service runs with no API key
- [ ] `AiRpcClient.chat(message)` returns a `ChatOut`

**Verify:** `uv run pytest services/ai/tests/test_app.py rpc/tests/test_ai_client.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests**

`services/ai/tests/test_app.py`:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from rpc.server import add_rpc_error_handler, create_rpc_router
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn
from ai_service.rpc_tools import build_ai_registry


class FakeContent:
    def list_projects(self, featured=None):
        return []

    def get_project(self, slug):
        raise AssertionError("unused")


def _client():
    chat = Chat(llm=FakeLLMProvider([LLMTurn("end_turn", text="hello from ai")]), content=FakeContent())
    app = FastAPI()
    add_rpc_error_handler(app)
    app.include_router(create_rpc_router(build_ai_registry(chat), "t"))
    return TestClient(app)


def test_chat_tool():
    r = _client().post("/rpc/chat", json={"message": "hi"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json() == {"reply": "hello from ai"}
```

`rpc/tests/test_ai_client.py`:
```python
import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.ai_rpc.client import AiRpcClient


def test_ai_client_chat():
    def handler(request):
        return httpx.Response(200, json={"reply": "ok"})
    c = AiRpcClient(ServiceClient("http://ai", static_token_provider("t"),
                                  transport=httpx.MockTransport(handler)))
    assert c.chat("hi").reply == "ok"
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/ai/tests/test_app.py rpc/tests/test_ai_client.py -v`
Expected: FAIL (missing modules)

- [ ] **Step 3: Implement ai_rpc contracts + client**

`rpc/rpc/ai_rpc/__init__.py`:
```python
"""ai service contracts + typed client."""
```

`rpc/rpc/ai_rpc/contracts.py`:
```python
from pydantic import BaseModel


class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str
```

`rpc/rpc/ai_rpc/client.py`:
```python
from typing import Protocol

from rpc.base import ServiceClient

from .contracts import ChatOut


class AiSource(Protocol):
    def chat(self, message: str) -> ChatOut: ...


class AiRpcClient:
    def __init__(self, client: ServiceClient):
        self._c = client

    def chat(self, message):
        return ChatOut.model_validate(self._c.call("chat", message=message))
```

- [ ] **Step 4: Implement `rpc_tools.py`**

```python
from rpc.ai_rpc.contracts import ChatIn, ChatOut
from rpc.server import ToolRegistry

from .chat import Chat


def build_ai_registry(chat: Chat) -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool("chat")
    def chat_tool(args: ChatIn) -> ChatOut:
        return ChatOut(reply=chat.reply(args.message))

    return reg
```

- [ ] **Step 5: Implement `config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    content_url: str = "http://localhost:8001"
    llm_provider: str = "fake"          # "anthropic" | "fake"
    llm_api_key: str = ""
    llm_base_url: str = ""              # e.g. the Vercel AI Gateway endpoint
    llm_model: str = "claude-haiku-4-5-20251001"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

- [ ] **Step 6: Implement `deps.py`**

```python
from functools import lru_cache

from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient

from .chat import Chat
from .config import Settings
from .llm import AnthropicProvider, FakeLLMProvider, LLMTurn


@lru_cache
def get_settings():
    return Settings()


def _build_llm(s):
    if s.llm_provider == "anthropic":
        return AnthropicProvider(api_key=s.llm_api_key, base_url=s.llm_base_url or None, model=s.llm_model)
    return FakeLLMProvider([LLMTurn("end_turn", text="Hi! Ask me about Logan's projects and work.")])


@lru_cache
def get_chat():
    s = get_settings()
    content = ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))
    return Chat(llm=_build_llm(s), content=content)
```

- [ ] **Step 7: Implement `main.py`**

```python
from fastapi import FastAPI

from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_chat, get_settings
from .rpc_tools import build_ai_registry

app = FastAPI(title="ai")
add_rpc_error_handler(app)
app.include_router(create_rpc_router(build_ai_registry(get_chat()), get_settings().service_token))


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Run to verify pass**

Run: `uv run pytest services/ai/tests/test_app.py rpc/tests/test_ai_client.py -v`
Expected: PASS

- [ ] **Step 9: End of Batch B3 — DO NOT commit.**

`End of Batch B3.` Suggested commit message for Logan:
```
add ai chat service with claude provider behind di
```

---

# Batch B4 — Web BFF

### Task 8: Web config, deps & client wiring

**Goal:** Give `web` its typed `Settings` and DI providers that build `ContentSource` and `AiSource` clients — the one place concrete clients are named.

**Files:**
- Create: `services/web/web_service/config.py`, `services/web/web_service/deps.py`, `services/web/web_service/templating.py`
- Test: `services/web/tests/test_deps.py`

**Acceptance Criteria:**
- [ ] `Settings` reads `SERVICE_TOKEN`, `CONTENT_URL`, `AI_URL` from env
- [ ] `get_content()` returns a `ContentRpcClient`; `get_ai()` returns an `AiRpcClient`
- [ ] `templating.templates` is a `Jinja2Templates` pointed at the templates dir

**Verify:** `uv run pytest services/web/tests/test_deps.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing test**

`services/web/tests/test_deps.py`:
```python
from rpc.ai_rpc.client import AiRpcClient
from rpc.content_rpc.client import ContentRpcClient
from web_service.deps import get_ai, get_content, get_settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("CONTENT_URL", "http://c:1")
    get_settings.cache_clear()
    assert get_settings().content_url == "http://c:1"


def test_clients_built():
    assert isinstance(get_content(), ContentRpcClient)
    assert isinstance(get_ai(), AiRpcClient)
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/web/tests/test_deps.py -v`
Expected: FAIL (missing modules)

- [ ] **Step 3: Implement `config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_token: str = "dev-token"
    content_url: str = "http://localhost:8001"
    ai_url: str = "http://localhost:8002"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

- [ ] **Step 4: Implement `deps.py`**

```python
from functools import lru_cache

from rpc.ai_rpc.client import AiRpcClient, AiSource
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient, ContentSource

from .config import Settings


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_content() -> ContentSource:
    s = get_settings()
    return ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))


@lru_cache
def get_ai() -> AiSource:
    s = get_settings()
    return AiRpcClient(ServiceClient(s.ai_url, static_token_provider(s.service_token)))
```

- [ ] **Step 5: Implement `templating.py`**

```python
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run pytest services/web/tests/test_deps.py -v`
Expected: PASS

- [ ] **Step 7: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 9: Web routes, templates, HTMX & static assets

**Goal:** Build the four routes (`/`, `/work`, `/work/{slug}`, `/chat`) with Jinja templates, an HTMX chat partial, vendored HTMX/Alpine, base CSS, and graceful degradation when a backend RPC call fails — tested with injected fakes.

**Files:**
- Create: `services/web/web_service/routes/__init__.py`, `routes/home.py`, `routes/work.py`, `routes/chat.py`, `web_service/main.py`
- Create templates: `templates/base.html`, `templates/index.html`, `templates/work_list.html`, `templates/work_detail.html`, `templates/chat.html`, `templates/_chat_reply.html`
- Create static: `static/styles.css`, `static/htmx.min.js`, `static/alpine.min.js`
- Test: `services/web/tests/test_routes.py`

**Acceptance Criteria:**
- [ ] `/` renders featured project titles; `/work` lists all; `/work/{slug}` renders body; `/work/missing` → 404 page
- [ ] `POST /chat` (form field `message`) returns the `_chat_reply.html` partial with the reply
- [ ] When the injected client raises `RPCError`, the page still renders with a visible fallback (no 500)

**Verify:** `uv run pytest services/web/tests/test_routes.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests** (`FastAPI` `dependency_overrides` inject fakes)

`services/web/tests/test_routes.py`:
```python
from fastapi.testclient import TestClient
from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from rpc.ai_rpc.contracts import ChatOut
from web_service.main import app
from web_service.deps import get_ai, get_content


class FakeContent:
    def list_projects(self, featured=None):
        items = [ProjectSummary(slug="this-website", title="This Website", featured=True)]
        return [p for p in items if featured is None or p.featured == featured]

    def get_project(self, slug):
        if slug != "this-website":
            from rpc.exceptions import NotFound
            raise NotFound(slug)
        return Project(slug=slug, title="This Website", body_html="<p>hello</p>")


class FakeAi:
    def chat(self, message):
        return ChatOut(reply=f"you said {message}")


class BrokenContent(FakeContent):
    def list_projects(self, featured=None):
        raise ServiceError("down")


def _client(content=None, ai=None):
    app.dependency_overrides[get_content] = lambda: content or FakeContent()
    app.dependency_overrides[get_ai] = lambda: ai or FakeAi()
    return TestClient(app, raise_server_exceptions=True)


def teardown_function():
    app.dependency_overrides.clear()


def test_home_lists_featured():
    r = _client().get("/")
    assert r.status_code == 200 and "This Website" in r.text


def test_work_detail():
    r = _client().get("/work/this-website")
    assert r.status_code == 200 and "hello" in r.text


def test_work_missing_404():
    assert _client().get("/work/nope").status_code == 404


def test_chat_partial():
    r = _client().post("/chat", data={"message": "hi"})
    assert r.status_code == 200 and "you said hi" in r.text


def test_home_degrades_gracefully():
    r = _client(content=BrokenContent()).get("/")
    assert r.status_code == 200 and "unavailable" in r.text.lower()
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest services/web/tests/test_routes.py -v`
Expected: FAIL (missing modules/templates)

- [ ] **Step 3: Implement routes** `services/web/web_service/routes/__init__.py` (empty), then:

`routes/home.py`:
```python
from fastapi import APIRouter, Depends, Request

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import RPCError

from ..deps import get_content
from ..templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, content: ContentSource = Depends(get_content)):
    try:
        featured = content.list_projects(featured=True)
        error = None
    except RPCError:
        featured, error = [], "Featured work is temporarily unavailable."
    return templates.TemplateResponse("index.html", {"request": request, "featured": featured, "error": error})
```

`routes/work.py`:
```python
from fastapi import APIRouter, Depends, Request

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import NotFound, RPCError

from ..deps import get_content
from ..templating import templates

router = APIRouter()


@router.get("/work")
def work_list(request: Request, content: ContentSource = Depends(get_content)):
    try:
        projects = content.list_projects()
        error = None
    except RPCError:
        projects, error = [], "Work is temporarily unavailable."
    return templates.TemplateResponse("work_list.html", {"request": request, "projects": projects, "error": error})


@router.get("/work/{slug}")
def work_detail(slug: str, request: Request, content: ContentSource = Depends(get_content)):
    try:
        project = content.get_project(slug)
    except NotFound:
        return templates.TemplateResponse(
            "work_detail.html", {"request": request, "project": None, "error": None}, status_code=404)
    except RPCError:
        return templates.TemplateResponse(
            "work_detail.html", {"request": request, "project": None, "error": "Temporarily unavailable."})
    return templates.TemplateResponse("work_detail.html", {"request": request, "project": project, "error": None})
```

`routes/chat.py`:
```python
from fastapi import APIRouter, Depends, Form, Request

from rpc.ai_rpc.client import AiSource
from rpc.exceptions import RPCError

from ..deps import get_ai
from ..templating import templates

router = APIRouter()


@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@router.post("/chat")
def chat_send(request: Request, message: str = Form(...), ai: AiSource = Depends(get_ai)):
    try:
        reply = ai.chat(message=message).reply
    except RPCError:
        reply = "The chat is temporarily unavailable — please try again shortly."
    return templates.TemplateResponse("_chat_reply.html", {"request": request, "message": message, "reply": reply})
```

- [ ] **Step 4: Implement `main.py`**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import chat, home, work

BASE = Path(__file__).parent
app = FastAPI(title="web")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(home.router)
app.include_router(work.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Implement templates**

`templates/base.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Logan Schwappach{% endblock %}</title>
  <link rel="stylesheet" href="/static/styles.css">
  <script src="/static/htmx.min.js" defer></script>
  <script src="/static/alpine.min.js" defer></script>
</head>
<body>
  <header class="nav">
    <a href="/" class="brand">Logan Schwappach</a>
    <nav><a href="/work">Work</a> <a href="/chat">Chat</a></nav>
  </header>
  <main class="container">{% block content %}{% endblock %}</main>
</body>
</html>
```

`templates/index.html`:
```html
{% extends "base.html" %}
{% block content %}
  <section class="hero">
    <h1>Backend developer</h1>
    <p>Python · microservices · HTMX</p>
  </section>
  <section>
    <h2>Featured work</h2>
    {% if error %}<p class="notice">{{ error }}</p>{% endif %}
    <ul class="cards">
      {% for p in featured %}
        <li><a href="/work/{{ p.slug }}"><strong>{{ p.title }}</strong>
          {% if p.year %}<span class="year">{{ p.year }}</span>{% endif %}</a></li>
      {% else %}
        {% if not error %}<li>Nothing featured yet.</li>{% endif %}
      {% endfor %}
    </ul>
  </section>
{% endblock %}
```

`templates/work_list.html`:
```html
{% extends "base.html" %}
{% block title %}Work — Logan Schwappach{% endblock %}
{% block content %}
  <h1>Work</h1>
  {% if error %}<p class="notice">{{ error }}</p>{% endif %}
  <ul class="cards">
    {% for p in projects %}
      <li><a href="/work/{{ p.slug }}"><strong>{{ p.title }}</strong> — {{ p.blurb }}</a></li>
    {% else %}
      {% if not error %}<li>No projects yet.</li>{% endif %}
    {% endfor %}
  </ul>
{% endblock %}
```

`templates/work_detail.html`:
```html
{% extends "base.html" %}
{% block title %}{{ project.title if project else "Not found" }}{% endblock %}
{% block content %}
  {% if project %}
    <article>
      <h1>{{ project.title }}</h1>
      <p class="meta">{{ project.role }}{% if project.tech %} · {{ project.tech | join(", ") }}{% endif %}</p>
      {% if project.highlights %}<ul>{% for h in project.highlights %}<li>{{ h }}</li>{% endfor %}</ul>{% endif %}
      <div class="body">{{ project.body_html | safe }}</div>
    </article>
  {% else %}
    <p class="notice">{{ error or "That project could not be found." }}</p>
    <p><a href="/work">← Back to work</a></p>
  {% endif %}
{% endblock %}
```

`templates/chat.html`:
```html
{% extends "base.html" %}
{% block title %}Chat — Logan Schwappach{% endblock %}
{% block content %}
  <h1>Ask about my work</h1>
  <div id="chat-log" class="chat-log"></div>
  <form hx-post="/chat" hx-target="#chat-log" hx-swap="beforeend" hx-on::after-request="this.reset()">
    <input name="message" placeholder="Ask me about Logan's projects…" autocomplete="off" required>
    <button type="submit">Send</button>
  </form>
{% endblock %}
```

`templates/_chat_reply.html`:
```html
<div class="msg user">{{ message }}</div>
<div class="msg bot">{{ reply }}</div>
```

- [ ] **Step 6: Base CSS** `static/styles.css`

```css
:root { --fg:#1a1a1a; --muted:#666; --accent:#4e4092; --bg:#fff; }
* { box-sizing: border-box; }
body { margin:0; font:16px/1.6 system-ui,sans-serif; color:var(--fg); background:var(--bg); }
.nav { display:flex; justify-content:space-between; align-items:center; padding:1rem 1.5rem; border-bottom:1px solid #eee; }
.nav a { color:var(--fg); text-decoration:none; margin-left:1rem; }
.brand { font-weight:600; margin-left:0; }
.container { max-width:720px; margin:0 auto; padding:2rem 1.5rem; }
.hero h1 { font-size:clamp(2rem,6vw,3.5rem); font-weight:300; letter-spacing:-0.02em; margin:0 0 .25rem; }
.cards { list-style:none; padding:0; display:grid; gap:.75rem; }
.cards a { color:var(--fg); text-decoration:none; display:block; padding:1rem; border:1px solid #eee; border-radius:8px; }
.cards a:hover { border-color:var(--accent); }
.year { color:var(--muted); margin-left:.5rem; }
.notice { color:#8a5000; background:#fff6e8; padding:.75rem 1rem; border-radius:8px; }
.meta { color:var(--muted); }
.chat-log { display:grid; gap:.5rem; margin-bottom:1rem; }
.msg { padding:.6rem .9rem; border-radius:10px; max-width:80%; }
.msg.user { background:#eff0ff; justify-self:end; }
.msg.bot { background:#f5f5f5; justify-self:start; }
form { display:flex; gap:.5rem; }
input[name=message] { flex:1; padding:.6rem .8rem; border:1px solid #ccc; border-radius:8px; }
button { padding:.6rem 1rem; border:0; background:var(--accent); color:#fff; border-radius:8px; cursor:pointer; }
```

- [ ] **Step 7: Vendor HTMX + Alpine** (pinned)

Run:
```bash
curl -fsSL https://unpkg.com/htmx.org@2.0.3/dist/htmx.min.js -o services/web/web_service/static/htmx.min.js
curl -fsSL https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js -o services/web/web_service/static/alpine.min.js
```
(If offline, create both files containing `// vendored later` — the pages still render; only interactivity is deferred.)

- [ ] **Step 8: Run to verify pass**

Run: `uv run pytest services/web/tests/test_routes.py -v`
Expected: PASS

- [ ] **Step 9: End of Batch B4 — DO NOT commit.**

`End of Batch B4.` Suggested commit message for Logan:
```
add web bff with htmx pages and graceful degradation
```

---

# Batch B5 — Integration & local dev

### Task 10: Dockerfiles + docker-compose (additive container path)

**Goal:** Provide a container path that runs all three services with one command, mirroring the honcho local loop. (Requires Docker; the app already runs without it via honcho.)

**Files:**
- Create: `services/content/Dockerfile`, `services/ai/Dockerfile`, `services/web/Dockerfile`, `docker-compose.yml`, `.dockerignore`

**Acceptance Criteria:**
- [ ] Each `Dockerfile` builds a service image with `uv` and runs its uvicorn app
- [ ] `docker-compose.yml` defines `content`/`ai`/`web` with env, ports (web→8000), `depends_on`, and healthchecks
- [ ] `docker compose config` validates (if Docker installed)

**Verify:** `docker compose config >/dev/null && echo OK` → `OK` (skip with a note if Docker is not installed; honcho path already proven)

**Steps:**

- [ ] **Step 1: `.dockerignore`**

```
.venv
**/__pycache__
.pytest_cache
.ruff_cache
docs
.git
```

- [ ] **Step 2: A Dockerfile per service** (identical except the final module). `services/content/Dockerfile`:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY . /app
RUN uv sync --package content-service --no-dev
EXPOSE 8001
CMD ["uv", "run", "--package", "content-service", "uvicorn", "content_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

`services/ai/Dockerfile` — same, but copy `services/ai`, `--package ai-service`, port `8002`, `CMD ... ai_service.main:app ... --port 8002`.

`services/web/Dockerfile` — same, but copy `services/web`, `--package web-service`, port `8000`, `CMD ... web_service.main:app ... --port 8000`.

- [ ] **Step 3: `docker-compose.yml`**

```yaml
services:
  content:
    build: { context: ., dockerfile: services/content/Dockerfile }
    environment: { SERVICE_TOKEN: dev-token }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8001/health').status==200 else sys.exit(1)"]
      interval: 5s
      retries: 5
  ai:
    build: { context: ., dockerfile: services/ai/Dockerfile }
    environment:
      SERVICE_TOKEN: dev-token
      CONTENT_URL: http://content:8001
      LLM_PROVIDER: ${LLM_PROVIDER:-fake}
      LLM_API_KEY: ${LLM_API_KEY:-}
      LLM_BASE_URL: ${LLM_BASE_URL:-}
    depends_on: { content: { condition: service_healthy } }
  web:
    build: { context: ., dockerfile: services/web/Dockerfile }
    environment:
      SERVICE_TOKEN: dev-token
      CONTENT_URL: http://content:8001
      AI_URL: http://ai:8002
    ports: ["8000:8000"]
    depends_on: [content, ai]
```

- [ ] **Step 4: Generate the lockfile the Dockerfiles reference**

Run: `uv lock`
Expected: `uv.lock` created/updated at repo root.

- [ ] **Step 5: Verify (Docker-gated)**

Run: `docker compose config >/dev/null && echo OK`
Expected: `OK`. If `docker: command not found`, note it and rely on the honcho loop + Task 11's in-process e2e (which needs no Docker).

- [ ] **Step 6: Report task complete — DO NOT commit.** `Tests green — continue to next task.`

---

### Task 11: End-to-end smoke test (full stack, in-process)

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation ("runs cleanly … locally" as the v1 target). It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Goal:** Prove the whole system works together — `web → content` and `web → ai → content` — with a deterministic, in-process test that needs no network, no Docker, and no API key (using the injected-transport DI seam and the fake LLM), plus a curl smoke script for a running stack.

**Files:**
- Create: `tests/e2e/__init__.py`, `tests/e2e/test_stack.py`, `scripts/smoke.sh`

**Acceptance Criteria:**
- [ ] `web`'s `/` renders a real project title fetched from the actual `content` app (not a fake) over the RPC path
- [ ] `web`'s `POST /chat` returns a reply produced by the actual `ai` app (fake LLM), which itself called `content` over RPC
- [ ] The e2e test passes offline with `LLM_PROVIDER=fake`
- [ ] `scripts/smoke.sh` returns non-zero if any of web `/health`, `/`, `/work` is not HTTP 200

**Verify:** `uv run pytest tests/e2e -v` → all pass

**Steps:**

- [ ] **Step 1: Write the e2e test** — bridge `web`'s injected `ServiceClient` transport to the real content/ai apps via `TestClient`

`tests/e2e/__init__.py`: (empty)

`tests/e2e/test_stack.py`:
```python
import httpx
from fastapi.testclient import TestClient

from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient
from rpc.ai_rpc.client import AiRpcClient

# real service apps
from content_service.main import app as content_app
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn, ToolUse
from ai_service.rpc_tools import build_ai_registry
from rpc.server import create_rpc_router, add_rpc_error_handler
from fastapi import FastAPI

from web_service.main import app as web_app
from web_service.deps import get_content, get_ai

TOKEN = "dev-token"


def _bridge(app):
    """An httpx MockTransport that forwards requests into a Starlette TestClient (in-process)."""
    tc = TestClient(app)

    def handler(request: httpx.Request) -> httpx.Response:
        r = tc.request(request.method, request.url.path,
                       content=request.content, headers=dict(request.headers))
        return httpx.Response(r.status_code, content=r.content,
                              headers={"content-type": r.headers.get("content-type", "application/json")})
    return httpx.MockTransport(handler)


def _content_client():
    return ContentRpcClient(ServiceClient("http://content", static_token_provider(TOKEN),
                                          transport=_bridge(content_app)))


def _ai_app():
    # a real ai app whose Chat grounds via the real content app, driven by a scripted fake LLM
    chat = Chat(
        llm=FakeLLMProvider([
            LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "this-website"})]),
            LLMTurn("end_turn", text="Logan built This Website as a microservices demo."),
        ]),
        content=_content_client(),
    )
    app = FastAPI()
    add_rpc_error_handler(app)
    app.include_router(create_rpc_router(build_ai_registry(chat), TOKEN))
    return app


def _web():
    web_app.dependency_overrides[get_content] = _content_client
    web_app.dependency_overrides[get_ai] = lambda: AiRpcClient(
        ServiceClient("http://ai", static_token_provider(TOKEN), transport=_bridge(_ai_app())))
    return TestClient(web_app)


def teardown_module():
    web_app.dependency_overrides.clear()


def test_home_shows_real_content():
    r = _web().get("/")
    assert r.status_code == 200 and "This Website" in r.text


def test_chat_round_trips_through_ai_and_content():
    r = _web().post("/chat", data={"message": "tell me about this website"})
    assert r.status_code == 200 and "This Website" in r.text
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/e2e -v`
Expected: FAIL first run only if any wiring is off; fix until green.

- [ ] **Step 3: Add `tests/e2e` to test discovery** (root `pyproject.toml`)

Append to root `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["rpc/tests", "services/content/tests", "services/ai/tests", "services/web/tests", "tests/e2e"]
```

- [ ] **Step 4: Write `scripts/smoke.sh`** (for a running stack via honcho or compose)

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://localhost:8000}"
for path in /health / /work; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
  echo "$path -> $code"
  [ "$code" = "200" ] || { echo "FAIL: $path returned $code"; exit 1; }
done
echo "smoke OK"
```
Then: `chmod +x scripts/smoke.sh`

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS across all packages including `tests/e2e`.

- [ ] **Step 6: (Gate evidence) Manual live check** — capture output

Terminal 1: `uv run honcho -f Procfile.dev start`
Terminal 2: `bash scripts/smoke.sh` → expect each path `-> 200` and `smoke OK`.

- [ ] **Step 7: End of Batch B5 — DO NOT commit.**

`End of Batch B5.` Suggested commit message for Logan:
```
add docker setup and end-to-end smoke test
```

---

## Notes for the executor

- **No commits.** Stop at each `End of Batch` marker and ask Logan to commit with the suggested message. Never `git add` anything under `docs/`.
- **Run tests with `uv run pytest`** from the repo root; `uv` resolves the workspace automatically.
- **Offline by default.** `LLM_PROVIDER=fake` means the AI service and all tests run with no API key. Real Claude is opt-in via `LLM_PROVIDER=anthropic` + `LLM_API_KEY` (+ `LLM_BASE_URL` for the Vercel AI Gateway).
- **If a `curl` vendoring step fails offline** (Task 9 Step 7), create placeholder JS files so pages render; interactivity is added when back online.
