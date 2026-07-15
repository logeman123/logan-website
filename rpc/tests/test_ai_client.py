import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.ai_rpc.client import AiRpcClient


def test_ai_client_chat():
    def handler(request):
        return httpx.Response(200, json={"reply": "ok"})
    c = AiRpcClient(ServiceClient("http://ai", static_token_provider("t"),
                                  transport=httpx.MockTransport(handler)))
    assert c.chat("hi").reply == "ok"
