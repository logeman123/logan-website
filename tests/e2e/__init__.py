"""Marks ``tests/e2e`` as a Python package for the end-to-end test suite.

This file is intentionally (almost) empty -- its only job is to make
``tests/e2e`` an importable package so pytest collects the modules inside it and
so relative imports resolve. The interesting work lives in ``test_stack.py``,
which wires the THREE real service apps (web, ai, content) together IN-PROCESS
via an httpx ``MockTransport`` -> Starlette ``TestClient`` bridge -- no sockets,
no servers, no Docker -- to prove the full web -> ai -> content RPC path works.
"""
