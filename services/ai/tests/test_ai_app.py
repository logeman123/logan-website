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
