"""Tests for the web BFF's route handlers, in full isolation from the backends.

The web service owns NO data -- every route orchestrates the content and ai
services over RPC. That makes it the perfect place to demonstrate two patterns:

* **Injecting fakes via ``app.dependency_overrides``.** The routes depend on the
  ``ContentSource`` / ``AiSource`` Protocols through FastAPI ``Depends(get_content
  / get_ai)``. Here we replace those providers with in-memory fakes, so the
  routes exercise real templating and real control flow but never touch a
  socket. This is dependency inversion paying off: the fakes only need to
  *structurally* match the Protocol (right method names/shapes), no subclassing.

* **Graceful degradation.** Every route is supposed to catch ``RPCError`` (the
  shared base of ``ServiceError`` etc.) and render a friendly fallback instead
  of returning a 500. We prove that by injecting "broken" fakes that raise
  ``ServiceError`` -- the same exception type a genuinely unreachable backend
  would produce -- and asserting the response is still 200 with fallback copy.
"""

from fastapi.testclient import TestClient
from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import NotFound, ServiceError
from rpc.ai_rpc.contracts import ChatOut
from web_service.main import app
from web_service.deps import get_ai, get_content


class FakeContent:
    """A stand-in for the content service that structurally satisfies ContentSource.

    No inheritance or registration is needed -- because ``ContentSource`` is a
    ``typing.Protocol``, having ``list_projects`` and ``get_project`` with the
    right shapes is enough for this object to be injected wherever a real
    ``ContentRpcClient`` would go.
    """

    def list_projects(self, featured=None):
        # Return typed contract objects (ProjectSummary), exactly like the real
        # client would after decoding JSON -- so templates see identical types.
        items = [ProjectSummary(slug="this-website", title="This Website", featured=True)]
        # Mimic the real service's optional ``featured`` filter semantics.
        return [p for p in items if featured is None or p.featured == featured]

    def get_project(self, slug):
        # Reproduce the real not-found behavior: unknown slug -> NotFound, which
        # the route maps to a 404. Known slug -> a full Project with body HTML.
        if slug != "this-website":
            raise NotFound(slug)
        return Project(slug=slug, title="This Website", body_html="<p>hello</p>")


class FakeAi:
    """Deterministic AiSource fake -- echoes the message so the route's output is checkable."""

    def chat(self, message):
        return ChatOut(reply=f"you said {message}")


class BrokenContent(FakeContent):
    """A content fake whose every call fails, simulating an unreachable/erroring backend.

    It raises ``ServiceError`` -- the SAME RPCError subclass that ``ServiceClient``
    produces when the real content service is down or returns 500 -- so the
    degradation tests below genuinely exercise the route's ``except RPCError`` path.
    """

    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


class BrokenAi:
    """The ai counterpart to BrokenContent: chat always fails with ServiceError."""

    def chat(self, message):
        raise ServiceError("down")


def _client(content=None, ai=None):
    """Build a TestClient with the content/ai dependencies overridden by fakes.

    ``app.dependency_overrides`` is FastAPI's built-in DI seam: it swaps the
    provider function (``get_content`` / ``get_ai``) for our lambda, so any route
    that does ``Depends(get_content)`` receives the fake instead of the real RPC
    client. Defaults to the healthy fakes; pass a broken one to test degradation.
    """
    app.dependency_overrides[get_content] = lambda: content or FakeContent()
    app.dependency_overrides[get_ai] = lambda: ai or FakeAi()
    # raise_server_exceptions=True: if a route ever leaked an unhandled exception
    # (i.e. failed to degrade gracefully), the test would error out loudly rather
    # than quietly returning a 500 -- which is what we want to catch.
    return TestClient(app, raise_server_exceptions=True)


def teardown_function():
    # Overrides live on the shared module-level ``app``, so clear them after each
    # test to stop one test's fakes from bleeding into the next.
    app.dependency_overrides.clear()


def test_home_under_construction():
    # "/" is intentionally a minimal under-construction placeholder; it needs no
    # backend at all. We assert the identifying copy and the static asset ref.
    r = _client().get("/")
    assert r.status_code == 200
    assert "Logan Schwappach" in r.text
    assert "Under Construction" in r.text
    assert "/static/construction.gif" in r.text


def test_work_detail():
    # /work/{slug} calls content.get_project(slug) and renders its body_html.
    # "hello" comes from the FakeContent body, proving the fetched project made
    # it into the template.
    r = _client().get("/work/this-website")
    assert r.status_code == 200 and "hello" in r.text


def test_work_missing_404():
    # An unknown slug -> FakeContent raises NotFound -> the route returns a real
    # 404 (a *missing* resource is different from a *degraded* backend below).
    assert _client().get("/work/nope").status_code == 404


def test_chat_partial():
    # /chat is an HTMX endpoint that swaps in an HTML partial. Posting form data
    # calls ai.chat("hi"); FakeAi echoes it, so the reply appears in the partial.
    r = _client().post("/chat", data={"message": "hi"})
    assert r.status_code == 200 and "you said hi" in r.text


def test_work_list_degrades():
    # Graceful degradation: content is down (BrokenContent raises ServiceError),
    # yet /work must still return 200 with an "unavailable" message rather than
    # a 500. This is the ``except RPCError`` fallback in action.
    r = _client(content=BrokenContent()).get("/work")
    assert r.status_code == 200 and "unavailable" in r.text.lower()


def test_work_detail_degrades_on_rpcerror():
    # Same degradation contract for the detail route: a backend RPC failure (not
    # a missing slug) yields a "temporarily" unavailable fallback at 200, NOT a
    # 404 and NOT a 500.
    r = _client(content=BrokenContent()).get("/work/this-website")
    assert r.status_code == 200 and "temporarily" in r.text.lower()


def test_chat_degrades():
    # The ai service being down must not break the chat UI: BrokenAi raises
    # ServiceError, and the route renders a "temporarily unavailable" partial at
    # 200 so the page keeps working.
    r = _client(ai=BrokenAi()).post("/chat", data={"message": "hi"})
    assert r.status_code == 200 and "temporarily unavailable" in r.text.lower()
