"""The LLM abstraction layer for the ai service — "what talks to the model".

This module is a textbook example of **dependency inversion via a Protocol**. The rest of
the ai service (specifically ``chat.Chat``) depends only on the *shape* ``LLMProvider``,
never on a concrete SDK. That gives us two interchangeable implementations behind one seam:

    LLMProvider (Protocol / the contract)
        ├── AnthropicProvider  -> real Claude, via the ``anthropic`` SDK
        └── FakeLLMProvider    -> deterministic scripted turns (tests + offline dev)

Because ``Chat`` accepts any object with a ``run(...)`` method, we can:
  * run the entire stack offline with the fake (the default — see deps.py), and
  * unit-test the agentic loop with no network by scripting exact model turns.

The other job of this module is to **normalize** the provider's output. Different
providers return different response shapes, so ``run`` translates whatever the model
said into two tiny, provider-agnostic value objects — ``LLMTurn`` and ``ToolUse`` —
that ``chat.py`` can consume without knowing anything about Anthropic's message format.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolUse:
    """One request-to-call-a-tool emitted by the model within a single turn.

    When the model decides it needs data it doesn't have, it doesn't answer directly —
    it emits a ``tool_use`` block naming a tool and its arguments. We capture that as this
    normalized value:

    * ``id``    — the model-assigned id; we MUST echo it back on the matching tool_result
                  so the model can pair the answer with its request (see chat.py).
    * ``name``  — which tool to run (e.g. "get_project"); dispatched by tools.execute_tool.
    * ``input`` — the arguments dict the model chose (e.g. ``{"slug": "..."}``).
    """

    id: str
    name: str
    input: dict


@dataclass
class LLMTurn:
    """The normalized result of ONE model invocation — the unit the chat loop reasons about.

    ``stop_reason`` is the important control signal for the agentic loop in chat.py:
    ``"tool_use"`` means "I want tools run, then call me again", whereas ``"end_turn"``
    (or anything else) means "I'm done, here's the final answer". ``text`` holds any prose
    the model produced, and ``tool_uses`` holds the tool-call requests (empty when the
    model just answered). ``field(default_factory=list)`` gives each instance its OWN empty
    list rather than sharing one mutable default across all instances.
    """

    stop_reason: str            # "tool_use" | "end_turn" | ...
    text: str = ""
    tool_uses: list[ToolUse] = field(default_factory=list)


class LLMProvider(Protocol):
    """Structural contract every LLM backend must satisfy (the dependency-inversion seam).

    This is a ``typing.Protocol``: a class is a valid ``LLMProvider`` simply by *having* a
    matching ``run`` method — it need not inherit from anything. ``chat.Chat`` is typed
    against this Protocol, so it is decoupled from both concrete providers below. Note the
    keyword-only (``*``) parameters mirror the Anthropic Messages API shape: a ``system``
    prompt, the running ``messages`` transcript, and the available ``tools`` specs.
    """

    def run(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMTurn: ...


class AnthropicProvider:
    """Real provider: calls Anthropic's Messages API and normalizes the reply to an LLMTurn.

    Structurally implements ``LLMProvider`` (no explicit inheritance needed). Configuration
    is injected — the API key, model, and (crucially) an optional ``base_url`` — so this one
    class can talk either to Anthropic directly OR through a proxy such as the Vercel AI
    Gateway just by pointing ``base_url`` at the gateway. deps.py decides which.
    """

    def __init__(self, *, api_key, base_url=None, model="claude-haiku-4-5-20251001", max_tokens=1024):
        # Import the SDK lazily, INSIDE __init__, so that merely importing this module (or
        # constructing the FakeLLMProvider) never requires the ``anthropic`` package to be
        # installed. It's only needed on the real path, which keeps offline dev dependency-light.
        from anthropic import Anthropic
        # base_url is the injection point for the AI Gateway: pass it to reroute all traffic
        # through the proxy; omit it (None) to hit Anthropic's default public endpoint.
        self._client = Anthropic(api_key=api_key, base_url=base_url) if base_url else Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def run(self, *, system, messages, tools):
        # One synchronous round-trip to the model. ``system``/``messages``/``tools`` are
        # forwarded straight through — the chat loop already built them in Anthropic's format.
        resp = self._client.messages.create(
            model=self._model, max_tokens=self._max_tokens,
            system=system, messages=messages, tools=tools,
        )
        # An Anthropic response ``content`` is a LIST of typed blocks. Concatenate the prose
        # from every "text" block into a single string...
        text = "".join(b.text for b in resp.content if b.type == "text")
        # ...and translate every "tool_use" block into our provider-agnostic ToolUse value
        # (copying b.input into a plain dict so nothing downstream depends on SDK types).
        tool_uses = [ToolUse(id=b.id, name=b.name, input=dict(b.input))
                     for b in resp.content if b.type == "tool_use"]
        # Hand back the normalized turn; chat.py branches on stop_reason from here.
        return LLMTurn(stop_reason=resp.stop_reason, text=text, tool_uses=tool_uses)


class FakeLLMProvider:
    """Deterministic provider for tests and offline dev — returns scripted turns in order."""

    # WHY this exists: it is the DEFAULT provider (deps.py), which is what lets the whole
    # three-service stack run with no API key and no network. In tests it is the key to
    # exercising the agentic loop deterministically — e.g. the chat e2e scripts a first turn
    # that requests a tool and a second turn that echoes the tool result, genuinely proving
    # the ai -> content hop happened. Because it also satisfies the LLMProvider Protocol
    # structurally, Chat cannot tell it apart from the real thing.

    def __init__(self, turns: list[LLMTurn]):
        # Copy the caller's list so later external mutation can't change our script, and
        # start a cursor at the first turn.
        self._turns = list(turns)
        self._i = 0

    def run(self, *, system, messages, tools):
        # Ignore the inputs entirely and replay the next scripted turn. ``min(...)`` clamps
        # the cursor to the last turn, so if the loop calls us more times than we have turns,
        # we keep returning the final one instead of raising IndexError.
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return turn
