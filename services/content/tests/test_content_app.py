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
