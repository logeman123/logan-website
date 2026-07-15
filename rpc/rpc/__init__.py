"""Shared RPC layer: thin client, server-side tool registry, typed contracts.

This package is the beating heart of the whole system — the common language every service
speaks. There are three FastAPI microservices (web BFF, content, ai) plus this shared library;
the services never talk to each other in bespoke ways, they all go through the plumbing defined
here. Understanding these four modules is understanding how the whole monorepo fits together.

The pieces, and where each lives:

  * ``exceptions`` — the shared error vocabulary (``RPCError`` and friends) and the two-way
    mapping between those classes and HTTP status codes. This is what lets a failure keep its
    meaning as it crosses the wire, and lets every caller degrade with one ``except RPCError``.
  * ``base`` — the ``ServiceClient`` (the *caller* side). Fully dependency-injected: address,
    auth, and transport are all supplied from outside, which is what makes the in-process test
    bridge and swappable backends possible. Also handles token caching and the crucial wrapping
    of transport failures into ``ServiceError`` for graceful degradation.
  * ``server`` — the ``ToolRegistry`` + router (the *callee* side). A service registers handlers
    and this exposes them at ``POST /rpc/<tool>`` / ``GET /rpc/``. The discovery surface doubles
    as the AI/MCP tool catalogue the ai service's agentic loop consumes.

This ``__init__`` is the package's public face: it re-exports the handful of names that the
services and typed clients actually import, so downstream code writes ``from rpc import
ServiceClient`` instead of reaching into submodules. ``__all__`` pins that public API.
"""

# Client side: the injectable ServiceClient and the simplest token-provider factory.
from rpc.base import ServiceClient, static_token_provider
# The shared error hierarchy plus the status-code -> exception reconstructor used by the client.
from rpc.exceptions import (
    AuthError,
    InvalidRequest,
    NotFound,
    RPCError,
    ServiceError,
    error_for_status,
)
# Server side: the tool registry, the router factory, and the RPCError -> HTTP-status handler.
from rpc.server import ToolRegistry, add_rpc_error_handler, create_rpc_router

# The explicit public API of the ``rpc`` package — the names ``from rpc import *`` exposes and,
# more importantly, the curated set the services are expected to depend on.
__all__ = [
    "RPCError",
    "InvalidRequest",
    "AuthError",
    "NotFound",
    "ServiceError",
    "error_for_status",
    "ServiceClient",
    "static_token_provider",
    "ToolRegistry",
    "create_rpc_router",
    "add_rpc_error_handler",
]
