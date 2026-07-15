"""Publishes the ai service's capabilities on the shared RPC surface.

This is the thin adapter that turns the pure-Python ``Chat`` object into a network-callable
"tool". The shared ``rpc`` library defines the convention: you register named tools on a
``ToolRegistry``, and ``create_rpc_router`` (used in main.py) mounts every registered tool at
``POST /rpc/<name>`` and lists them at ``GET /rpc/``.

The request/response *contracts* (``ChatIn`` / ``ChatOut``) live in the shared
``rpc.ai_rpc.contracts`` module — NOT here — because they are the single source of truth
imported by BOTH this service (to validate/serialize) and its callers (the web BFF's
AiRpcClient, to build requests and parse replies). Defining them once is what keeps the two
sides of the wire in lockstep.

So the full chain for a chat request is:
    web BFF --HTTP POST /rpc/chat--> this "chat" tool --> Chat.reply --> (agentic loop) -->
    ai --HTTP /rpc/get_project--> content, and the answer flows back the same way.
"""

from rpc.ai_rpc.contracts import ChatIn, ChatOut
from rpc.server import ToolRegistry

from .chat import Chat


def build_ai_registry(chat: Chat) -> ToolRegistry:
    """Build the ToolRegistry advertising this service's RPC tools.

    ``chat`` is injected (constructed in deps.py) rather than built here — this function's
    only job is to bind that ready-made Chat object to a named endpoint. Returns the
    registry, which main.py feeds to ``create_rpc_router`` to produce the FastAPI routes.
    """
    reg = ToolRegistry()

    # Register a single tool named "chat". The decorator wires this function to
    # ``POST /rpc/chat``; the ``args: ChatIn`` annotation tells the rpc layer how to parse &
    # validate the incoming JSON body, and the ``-> ChatOut`` return is serialized to JSON.
    @reg.tool("chat")
    def chat_tool(args: ChatIn) -> ChatOut:
        # Delegate straight to the injected Chat (which runs the agentic tool-use loop) and
        # wrap the resulting string in the typed ChatOut contract for the response.
        return ChatOut(reply=chat.reply(args.message))

    return reg
