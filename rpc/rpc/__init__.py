"""Shared RPC layer: thin client, server-side tool registry, typed contracts."""

from rpc.base import ServiceClient, static_token_provider
from rpc.exceptions import (
    AuthError,
    InvalidRequest,
    NotFound,
    RPCError,
    ServiceError,
    error_for_status,
)
from rpc.server import ToolRegistry, add_rpc_error_handler, create_rpc_router

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
