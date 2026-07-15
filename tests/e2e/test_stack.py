"""End-to-end tests that wire the THREE real service apps together IN-PROCESS.

This is the most important test in the suite for understanding how the whole
system fits together, and it is only possible because of the dependency-inversion
seams built into every layer. There are no sockets, no running servers, and no
Docker here -- yet the REAL web, ai, and content FastAPI apps genuinely call one
another over the project's HTTP+JSON RPC convention.

The trick: the in-process bridge (``_bridge`` below)
----------------------------------------------------
``rpc.base.ServiceClient`` takes its httpx ``transport`` as an injected
dependency. Normally that transport opens real network connections. Here we
instead inject an ``httpx.MockTransport`` whose handler forwards every "network"
request straight into a Starlette ``TestClient`` for the target app. So when the
web app's ``ContentRpcClient`` thinks it is POSTing to ``http://content/rpc/...``,
the bytes actually travel function-call-deep into the real content app and back.
This is the payoff of "DI at the wire level" -- swap the transport, and the same
client code talks to a live server or to an in-process app with zero changes.

The assembled topology mirrors production exactly:

    web_app  --(bridge)-->  ai_app  --(bridge)-->  content_app
       |                                                ^
       +------------------(bridge)-----------------------+
       (web also calls content directly for the /work listing)

Why the fake LLM still makes this a real test (``ToolEchoingLLM`` below)
------------------------------------------------------------------------
The ai service's ``Chat`` runs an agentic tool-use loop. To keep the test
deterministic and offline we inject a fake LLM -- but a naive fake that just
returns a canned string would prove nothing about the ai -> content hop. Instead
this fake FIRST asks for the ``get_project`` tool, then on its SECOND turn echoes
back whatever tool_result the loop fed it. So the final chat reply can only
contain the expected content if the ai service really executed the tool, really
made the RPC call into the content app, and really got data back. The fake LLM
thus *forces* the ai -> content RPC hop to happen for the assertion to pass.
"""

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

# The shared bearer token every RPC hop authenticates with. Because we control
# both ends in-process, one static secret is enough (static_token_provider).
TOKEN = "dev-token"


class ToolEchoingLLM:
    """First turn asks for get_project; second turn replies with the tool_result content it received.

    This deterministic ``LLMProvider`` (it structurally satisfies the Protocol via
    its ``run`` method) is what makes the chat e2e a genuine integration test. By
    demanding a tool on turn 1 and then parroting back the tool's result on turn
    2, it guarantees the final assistant reply is data-dependent on the ai ->
    content RPC hop actually having executed. A fake that ignored the tool result
    could pass without any cross-service call ever happening; this one cannot.
    """

    def __init__(self):
        # Track which turn we're on so ``run`` can behave differently across the
        # two round-trips the Chat loop makes.
        self._calls = 0

    def run(self, *, system, messages, tools):
        # ``run`` is called once per iteration of Chat's agentic loop. Its
        # signature matches the LLMProvider Protocol (system/messages/tools).
        self._calls += 1
        if self._calls == 1:
            # Turn 1: return a ``tool_use`` turn requesting get_project("this-website").
            # stop_reason="tool_use" tells the Chat loop to execute the tool (an
            # RPC call into the content app) and call us again with the results.
            # The "1" is the tool_use id used to pair the request with its result.
            return LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "this-website"})])
        # Turn 2: the Chat loop has appended a tool_result block to the transcript
        # containing whatever the content app returned. We reach into that last
        # message and echo the tool's payload back as our final answer -- so the
        # reply text is literally the data that came back over the RPC hop.
        last = messages[-1]
        tool_text = ""
        content = last.get("content")
        if isinstance(content, list):
            # The assistant/tool turn is a list of typed content blocks; find the
            # tool_result one and extract its content (the grounded project data).
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_text = block.get("content", "")
        # stop_reason="end_turn" tells the Chat loop we're done -> this text is the answer.
        return LLMTurn("end_turn", text=f"Here is what I found: {tool_text}")


def _bridge(app):
    """Build an httpx MockTransport that forwards requests into an in-process Starlette app.

    This is the single seam that makes the whole in-process topology possible.
    ``httpx.MockTransport`` lets us supply a plain Python callable that receives
    each outgoing ``httpx.Request`` and must return an ``httpx.Response`` -- no
    socket is ever opened. Our handler simply replays the request into a Starlette
    ``TestClient`` for the target ``app`` and repackages the result. When we later
    inject the returned transport into a ``ServiceClient`` (see ``_content_client``
    / ``_web``), the client's ordinary "POST to http://content/rpc/..." call is
    quietly rerouted, function-call-deep, into the real target app and back.
    """
    tc = TestClient(app)  # one in-process client bound to the destination app

    def handler(request: httpx.Request) -> httpx.Response:
        # Translate the httpx request the ServiceClient produced into an equivalent
        # TestClient call against the real app. Only the path is needed because the
        # TestClient is already bound to that specific app (the host in the URL is
        # a fiction that exists purely so the ServiceClient has a valid base_url).
        r = tc.request(request.method, request.url.path,
                       content=request.content, headers=dict(request.headers))
        # Repackage the TestClient response as the httpx.Response the transport must
        # hand back, preserving status and content-type so the RPC client decodes it
        # exactly as it would a real network response.
        return httpx.Response(r.status_code, content=r.content,
                              headers={"content-type": r.headers.get("content-type", "application/json")})
    return httpx.MockTransport(handler)


def _content_client():
    """A real ContentRpcClient wired to the real content app via the in-process bridge.

    This is the exact typed client production uses, with only its injected pieces
    swapped: ``static_token_provider(TOKEN)`` stands in for the real bearer-token
    source, and ``transport=_bridge(content_app)`` replaces the network transport
    with the in-process forwarder. Both the ai app (for grounding) and the web app
    (for the /work listing) reuse this factory, so both talk to the SAME real
    content app -- mirroring the production fan-out where two callers share content.
    """
    return ContentRpcClient(ServiceClient("http://content", static_token_provider(TOKEN),
                                          transport=_bridge(content_app)))


def _ai_app():
    """Assemble the REAL ai service app, but with its two collaborators injected as test doubles.

    The ai service is built exactly as in production -- a ``Chat`` object mounted
    as RPC tools via ``build_ai_registry`` + ``create_rpc_router`` behind the
    RPCError->status handler. The only substitutions are its injected dependencies:
    the LLM is the deterministic ``ToolEchoingLLM`` (so no API key / no network and
    a data-dependent reply), and ``content`` is the bridged ``_content_client`` (so
    the agentic tool-use loop's get_project call is a real RPC hop into the real
    content app). This is dependency inversion making a genuine integration test
    possible offline: the app under test is real; only the edges are controlled.
    """
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
    """Return a TestClient for the REAL web app, with both its RPC dependencies bridged.

    This completes the topology. Using FastAPI's ``dependency_overrides`` seam we
    point the web BFF's ``get_content`` at the shared bridged content client, and
    its ``get_ai`` at a bridged AiRpcClient whose transport forwards into a freshly
    built ``_ai_app()``. The result: a request to this TestClient runs the real web
    route, which makes a real RPC call across the bridge into the real ai app,
    which (for /chat) runs the real tool loop and makes a further real RPC call
    into the real content app -- all in-process, no sockets, exactly like prod.
    """
    web_app.dependency_overrides[get_content] = _content_client
    web_app.dependency_overrides[get_ai] = lambda: AiRpcClient(
        ServiceClient("http://ai", static_token_provider(TOKEN), transport=_bridge(_ai_app())))
    return TestClient(web_app)


def teardown_module():
    # The web app is a shared module-level singleton, so the dependency_overrides
    # installed by ``_web`` persist on it. Clear them once after this module's tests
    # finish so the bridged fakes don't leak into any other test module.
    web_app.dependency_overrides.clear()


def test_work_shows_real_content():
    # /work renders projects fetched from the real content app over the RPC bridge
    r = _web().get("/work")
    assert r.status_code == 200 and "This Website" in r.text


def test_chat_round_trips_through_ai_and_content():
    # The crown-jewel assertion. Posting to /chat drives the full three-hop path:
    # web -> ai (tool loop) -> content and back. Because ToolEchoingLLM only echoes
    # the tool_result it was handed, "This Website" can appear in the reply ONLY if
    # the ai service actually executed get_project over the RPC bridge into the real
    # content app and received the real project data. A stubbed reply could not fake
    # this -- so a green test proves every cross-service seam is genuinely connected.
    r = _web().post("/chat", data={"message": "tell me about this website"})
    assert r.status_code == 200 and "This Website" in r.text
