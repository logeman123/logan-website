from fastapi.testclient import TestClient
from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import NotFound, ServiceError
from rpc.ai_rpc.contracts import ChatOut
from web_service.main import app
from web_service.deps import get_ai, get_content


class FakeContent:
    def list_projects(self, featured=None):
        items = [ProjectSummary(slug="this-website", title="This Website", featured=True)]
        return [p for p in items if featured is None or p.featured == featured]

    def get_project(self, slug):
        if slug != "this-website":
            raise NotFound(slug)
        return Project(slug=slug, title="This Website", body_html="<p>hello</p>")


class FakeAi:
    def chat(self, message):
        return ChatOut(reply=f"you said {message}")


class BrokenContent(FakeContent):
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


class BrokenAi:
    def chat(self, message):
        raise ServiceError("down")


def _client(content=None, ai=None):
    app.dependency_overrides[get_content] = lambda: content or FakeContent()
    app.dependency_overrides[get_ai] = lambda: ai or FakeAi()
    return TestClient(app, raise_server_exceptions=True)


def teardown_function():
    app.dependency_overrides.clear()


def test_home_under_construction():
    r = _client().get("/")
    assert r.status_code == 200
    assert "Logan Schwappach" in r.text
    assert "Under Construction" in r.text
    assert "/static/construction.gif" in r.text


def test_work_detail():
    r = _client().get("/work/this-website")
    assert r.status_code == 200 and "hello" in r.text


def test_work_missing_404():
    assert _client().get("/work/nope").status_code == 404


def test_chat_partial():
    r = _client().post("/chat", data={"message": "hi"})
    assert r.status_code == 200 and "you said hi" in r.text


def test_work_list_degrades():
    r = _client(content=BrokenContent()).get("/work")
    assert r.status_code == 200 and "unavailable" in r.text.lower()


def test_work_detail_degrades_on_rpcerror():
    r = _client(content=BrokenContent()).get("/work/this-website")
    assert r.status_code == 200 and "temporarily" in r.text.lower()


def test_chat_degrades():
    r = _client(ai=BrokenAi()).post("/chat", data={"message": "hi"})
    assert r.status_code == 200 and "temporarily unavailable" in r.text.lower()
