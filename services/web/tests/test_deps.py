"""Tests for the web BFF's dependency-injection wiring (``web_service.deps``).

``deps.py`` is the ONE place in the web service where the abstract Protocols
(``ContentSource`` / ``AiSource``) get bound to concrete RPC clients pointed at
real hostnames. Everything else in the web service depends only on those
Protocols via FastAPI ``Depends(...)``. So this module verifies the two jobs
``deps.py`` actually does:

1. It reads configuration from the environment (``get_settings``).
2. It constructs the correct typed clients, pointed at the configured URLs,
   with no host baked in anywhere but here (``get_content`` / ``get_ai``).

A wrinkle worth understanding: each of those factories is wrapped in
``functools.lru_cache`` so it behaves as a process-wide singleton (build the
client/settings once, reuse forever). That caching is exactly what these tests
must defeat to observe fresh construction against per-test environment
variables -- hence the autouse ``_clear_caches`` fixture below.
"""

import pytest
from rpc.ai_rpc.client import AiRpcClient
from rpc.content_rpc.client import ContentRpcClient
from web_service.deps import get_ai, get_content, get_settings


@pytest.fixture(autouse=True)
def _clear_caches():
    """Reset the lru_cache on every DI factory before AND after each test.

    ``autouse=True`` means this runs automatically for every test in the module
    -- no test has to request it. Without this, the first test to call
    ``get_settings``/``get_content``/``get_ai`` would cache a client built from
    whatever environment existed then, and later tests' ``monkeypatch.setenv``
    would have no effect (the cached singleton would be returned unchanged).
    Clearing before yields a clean slate; clearing again after prevents this
    module from leaking a cached client into unrelated tests.
    """
    for fn in (get_settings, get_content, get_ai):
        fn.cache_clear()  # .cache_clear() is the method lru_cache adds to a wrapped fn
    yield  # <-- the test body runs here, between the two cache resets
    for fn in (get_settings, get_content, get_ai):
        fn.cache_clear()


def test_settings_from_env(monkeypatch):
    # Settings are environment-driven. ``monkeypatch.setenv`` sets the var only
    # for this test (pytest reverts it afterward). Because the cache was just
    # cleared, get_settings() re-reads the environment and picks up our value.
    monkeypatch.setenv("CONTENT_URL", "http://c:1")
    assert get_settings().content_url == "http://c:1"


def test_clients_built(monkeypatch):
    # Prove the factories build the RIGHT concrete client type AND point it at
    # the configured URL. This is the crux of the DI story: hostnames enter the
    # system here and nowhere else.
    monkeypatch.setenv("CONTENT_URL", "http://content-x:1")
    monkeypatch.setenv("AI_URL", "http://ai-x:2")
    c = get_content()
    a = get_ai()
    # Right implementations chosen for the Protocol-typed factories...
    assert isinstance(c, ContentRpcClient)
    assert isinstance(a, AiRpcClient)
    # ...and each typed client wraps a ServiceClient (stored as ``_c``) whose
    # injected base_url matches the env-configured target. Reaching into ``_c``
    # is a deliberate white-box check that the URL was threaded all the way down
    # to the wire-level client.
    assert c._c.base_url == "http://content-x:1"
    assert a._c.base_url == "http://ai-x:2"
