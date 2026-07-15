from rpc.content_rpc.client import ContentSource

from .llm import LLMProvider
from .tools import TOOL_SPECS, execute_tool

SYSTEM = (
    "You are the assistant on Logan Schwappach's personal website. "
    "Answer questions about Logan, his projects, and his work, using the tools to fetch real data "
    "rather than guessing. If asked something unrelated, briefly steer back to Logan's work."
)


class Chat:
    def __init__(self, *, llm: LLMProvider, content: ContentSource, max_steps: int = 5):
        self._llm = llm
        self._content = content
        self._max_steps = max_steps

    def reply(self, message: str) -> str:
        messages = [{"role": "user", "content": message}]
        for _ in range(self._max_steps):
            turn = self._llm.run(system=SYSTEM, messages=messages, tools=TOOL_SPECS)
            if turn.stop_reason != "tool_use":
                return turn.text
            assistant = []
            if turn.text:
                assistant.append({"type": "text", "text": turn.text})
            for tu in turn.tool_uses:
                assistant.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
            messages.append({"role": "assistant", "content": assistant})
            results = [
                {"type": "tool_result", "tool_use_id": tu.id,
                 "content": execute_tool(self._content, tu.name, tu.input)}
                for tu in turn.tool_uses
            ]
            messages.append({"role": "user", "content": results})
        return "Sorry — I couldn't complete that request."
