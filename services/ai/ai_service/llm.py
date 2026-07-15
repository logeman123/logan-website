from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class LLMTurn:
    stop_reason: str            # "tool_use" | "end_turn" | ...
    text: str = ""
    tool_uses: list[ToolUse] = field(default_factory=list)


class LLMProvider(Protocol):
    def run(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMTurn: ...


class AnthropicProvider:
    def __init__(self, *, api_key, base_url=None, model="claude-haiku-4-5-20251001", max_tokens=1024):
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key, base_url=base_url) if base_url else Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def run(self, *, system, messages, tools):
        resp = self._client.messages.create(
            model=self._model, max_tokens=self._max_tokens,
            system=system, messages=messages, tools=tools,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_uses = [ToolUse(id=b.id, name=b.name, input=dict(b.input))
                     for b in resp.content if b.type == "tool_use"]
        return LLMTurn(stop_reason=resp.stop_reason, text=text, tool_uses=tool_uses)


class FakeLLMProvider:
    """Deterministic provider for tests and offline dev — returns scripted turns in order."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = list(turns)
        self._i = 0

    def run(self, *, system, messages, tools):
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return turn
