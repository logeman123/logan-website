import httpx
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient


def test_typed_client_parses_models():
    def handler(request):
        if request.url.path == "/rpc/get_project":
            return httpx.Response(200, json={"slug": "a", "title": "A", "body_html": "<p/>"})
        return httpx.Response(200, json=[{"slug": "a", "title": "A"}])
    c = ContentRpcClient(ServiceClient("http://content", static_token_provider("t"),
                                       transport=httpx.MockTransport(handler)))
    assert c.get_project("a").title == "A"
    assert c.list_projects(featured=True)[0].slug == "a"
