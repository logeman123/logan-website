from rpc.ai_rpc.contracts import ChatIn, ChatOut
from rpc.server import ToolRegistry

from .chat import Chat


def build_ai_registry(chat: Chat) -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool("chat")
    def chat_tool(args: ChatIn) -> ChatOut:
        return ChatOut(reply=chat.reply(args.message))

    return reg
