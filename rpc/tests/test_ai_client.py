"""Unit test for ``AiRpcClient`` — the typed client for the ai service.

Role in the system
------------------
Mirror of ``test_content_client.py`` but for the ai side. ``AiRpcClient`` (in
``rpc/ai_rpc/client.py``) wraps a ``ServiceClient`` and exposes ``chat(...)``,
returning a typed ``ChatReply``. It structurally implements the ``AiSource``
Protocol that the web BFF depends on, so the web service can be handed this
concrete client through dependency injection without importing it directly.

The testing pattern
-------------------
Identical hermetic setup: an ``httpx.MockTransport`` fakes the ai service's
``/rpc/chat`` response so the test runs offline and asserts the reply is decoded
into the shared contract type.
"""

import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.ai_rpc.client import AiRpcClient


def test_ai_client_chat():
    """``chat`` sends the message and parses the JSON reply into ``ChatReply``.

    Accessing ``.reply`` (an attribute, not ``["reply"]``) confirms the typed
    client constructed the Pydantic contract from the faked response body.
    """
    def handler(request):
        return httpx.Response(200, json={"reply": "ok"})
    c = AiRpcClient(ServiceClient("http://ai", static_token_provider("t"),
                                  transport=httpx.MockTransport(handler)))
    assert c.chat("hi").reply == "ok"
