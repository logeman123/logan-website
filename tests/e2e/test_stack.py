import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_service.chat import Chat
from ai_service.llm import LLMTurn, ToolUse
from ai_service.rpc_tools import build_ai_registry

# real service apps
from content_service.main import app as content_app
from rpc.ai_rpc.client import AiRpcClient
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient
from rpc.server import add_rpc_error_handler, create_rpc_router
from web_service.deps import get_ai, get_content
from web_service.main import app as web_app

TOKEN = "dev-token"


class ToolEchoingLLM:
    """First turn asks for get_project; second turn replies with the tool_result content it received."""

    def __init__(self):
        self._calls = 0

    def run(self, *, system, messages, tools):
        self._calls += 1
        if self._calls == 1:
            return LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "this-website"})])
        # second call: pull the tool_result the Chat loop appended after executing the tool
        last = messages[-1]
        tool_text = ""
        content = last.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_text = block.get("content", "")
        return LLMTurn("end_turn", text=f"Here is what I found: {tool_text}")


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
    # a real ai app whose Chat grounds via the real content app, driven by a
    # tool-result-echoing fake LLM so the final reply genuinely depends on the RPC hop
    chat = Chat(
        llm=ToolEchoingLLM(),
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


def test_work_shows_real_content():
    # /work renders projects fetched from the real content app over the RPC bridge
    r = _web().get("/work")
    assert r.status_code == 200 and "This Website" in r.text


def test_chat_round_trips_through_ai_and_content():
    r = _web().post("/chat", data={"message": "tell me about this website"})
    assert r.status_code == 200 and "This Website" in r.text
