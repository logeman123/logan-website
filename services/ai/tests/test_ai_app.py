"""Integration-style test for the ai service's HTTP surface.

Role in the system
------------------
This wires the ai service the way it is assembled in production — ``Chat`` ->
``build_ai_registry`` -> ``create_rpc_router`` -> FastAPI app — and drives it
through the real HTTP layer. Where ``test_chat.py`` tests the loop in isolation,
this test proves the ``chat`` tool is correctly registered, routed at
``POST /rpc/chat``, authenticated, and that its reply is serialized as the
``ChatReply`` JSON contract. It shows the key architectural insight in action:
the RPC surface *is* the AI/MCP tool surface, exposed by the same
``create_rpc_router`` used by every service.

The testing pattern
-------------------
Everything runs in-process with zero network via two injected fakes plus
Starlette's ``TestClient``:

* ``FakeLLMProvider`` scripted with a single ``end_turn`` — the "model" answers
  immediately with fixed text, so no tools run and no content backend is needed.
* ``FakeContent`` satisfies ``Chat``'s dependency but is never exercised here.
* ``TestClient`` invokes the ASGI app directly, so we assert real routing/auth/
  serialization without a running server.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rpc.server import add_rpc_error_handler, create_rpc_router
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn
from ai_service.rpc_tools import build_ai_registry


class FakeContent:
    """Placeholder ``ContentSource`` to satisfy ``Chat``'s constructor.

    The scripted single-turn model answers directly without tool calls, so
    ``get_project`` should never run — the ``AssertionError`` documents and
    enforces that expectation.
    """
    def list_projects(self, featured=None):
        return []

    def get_project(self, slug):
        raise AssertionError("unused")


def _client():
    """Assemble the real ai service around fakes and wrap it in a TestClient.

    Mirrors production wiring exactly: build a ``Chat`` (with injected llm +
    content), turn it into an RPC tool registry via ``build_ai_registry``, mount
    that registry with ``create_rpc_router`` behind the shared bearer token
    ``"t"``, and install the RPCError->status handler. Only the llm/content
    dependencies are fakes; the HTTP plumbing is the genuine article.
    """
    chat = Chat(llm=FakeLLMProvider([LLMTurn("end_turn", text="hello from ai")]), content=FakeContent())
    app = FastAPI()
    add_rpc_error_handler(app)
    app.include_router(create_rpc_router(build_ai_registry(chat), "t"))
    return TestClient(app)


def test_chat_tool():
    """An authenticated ``POST /rpc/chat`` returns the reply as ``ChatReply`` JSON.

    The scripted model's text flows through ``Chat.reply`` and is serialized into
    ``{"reply": "hello from ai"}`` — confirming the end-to-end path from HTTP
    request to typed response contract works with the real router.
    """
    r = _client().post("/rpc/chat", json={"message": "hi"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json() == {"reply": "hello from ai"}
