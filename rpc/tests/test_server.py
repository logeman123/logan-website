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
