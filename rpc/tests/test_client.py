import json
import httpx
import pytest
from rpc.base import ServiceClient, static_token_provider
from rpc.exceptions import NotFound, ServiceError


def _client(handler, token="t"):
    return ServiceClient("http://svc", static_token_provider(token),
                         transport=httpx.MockTransport(handler))


def test_call_sends_bearer_and_returns_json():
    def handler(request):
        assert request.headers["authorization"] == "Bearer t"
        assert json.loads(request.content) == {"slug": "x"}
        assert request.url.path == "/rpc/get_project"
        return httpx.Response(200, json={"slug": "x", "ok": True})
    assert _client(handler).get_project(slug="x") == {"slug": "x", "ok": True}


def test_error_status_maps_to_exception():
    def handler(request):
        return httpx.Response(404, text="nope")
    with pytest.raises(NotFound):
        _client(handler).get_project(slug="missing")


def test_connect_error_maps_to_service_error():
    def handler(request):
        raise httpx.ConnectError("boom")
    with pytest.raises(ServiceError):
        _client(handler).call("x")


def test_token_is_cached():
    calls = {"n": 0}
    def provider():
        calls["n"] += 1
        return "tok", 3600.0
    def handler(request):
        return httpx.Response(200, json={})
    c = ServiceClient("http://svc", provider, transport=httpx.MockTransport(handler))
    c.call("a")
    c.call("b")
    assert calls["n"] == 1
