import pytest
from rpc.ai_rpc.client import AiRpcClient
from rpc.content_rpc.client import ContentRpcClient
from web_service.deps import get_ai, get_content, get_settings


@pytest.fixture(autouse=True)
def _clear_caches():
    for fn in (get_settings, get_content, get_ai):
        fn.cache_clear()
    yield
    for fn in (get_settings, get_content, get_ai):
        fn.cache_clear()


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("CONTENT_URL", "http://c:1")
    assert get_settings().content_url == "http://c:1"


def test_clients_built(monkeypatch):
    monkeypatch.setenv("CONTENT_URL", "http://content-x:1")
    monkeypatch.setenv("AI_URL", "http://ai-x:2")
    c = get_content()
    a = get_ai()
    assert isinstance(c, ContentRpcClient)
    assert isinstance(a, AiRpcClient)
    assert c._c.base_url == "http://content-x:1"
    assert a._c.base_url == "http://ai-x:2"
