"""Unit tests for the ``LLMProvider`` implementations (``ai_service.llm``).

Role in the system
------------------
The ai service hides the model behind an ``LLMProvider`` Protocol so the chat
loop never depends on a concrete SDK. Two implementations exist:

* ``FakeLLMProvider`` — deterministic and the DEFAULT, so the whole stack runs
  offline with no API key. You hand it a *script* of ``LLMTurn`` objects and it
  replays them one per ``run`` call; both ``Chat`` tests and e2e tests use it to
  drive the tool-use loop reproducibly.
* ``AnthropicProvider`` — the real Claude-backed provider (optionally pointed at
  the Vercel AI Gateway via ``base_url``). Its job is to translate the Anthropic
  SDK's response *content blocks* into the provider-neutral ``LLMTurn`` /
  ``ToolUse`` shapes the rest of the code understands.

The testing pattern
-------------------
For the fake we just assert its scripting/replay semantics. For the real
provider we do NOT touch the network or the SDK: we construct the object with
``__new__`` to skip ``__init__``, then hand-inject a fake ``_client`` whose
``messages.create`` returns a canned response built from ``SimpleNamespace``
stand-ins for SDK block objects. This isolates the pure translation logic
(SDK blocks -> ``LLMTurn``) from all I/O.
"""

from types import SimpleNamespace
from ai_service.llm import AnthropicProvider, FakeLLMProvider, LLMTurn, ToolUse


def test_fake_returns_scripted_then_repeats():
    """The fake replays its scripted turns in order, then sticks on the last one.

    We script two turns: a ``tool_use`` turn then an ``end_turn`` turn. The first
    two ``run`` calls return them in sequence; a third call past the end of the
    script returns the final turn again. That "repeat last" behavior means a test
    can't accidentally run off the end of its script and get an error — the loop
    just keeps seeing the terminal answer. ``run``'s keyword-only signature
    (``system``/``messages``/``tools``) matches the Protocol the real provider
    implements, so ``Chat`` can't tell the two apart.
    """
    p = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
                         LLMTurn("end_turn", text="done")])
    assert p.run(system="s", messages=[], tools=[]).stop_reason == "tool_use"  # 1st scripted turn
    assert p.run(system="s", messages=[], tools=[]).text == "done"             # 2nd scripted turn
    assert p.run(system="s", messages=[], tools=[]).text == "done"  # repeats last


def test_anthropic_maps_blocks(monkeypatch):
    """The real provider correctly flattens SDK content blocks into an ``LLMTurn``.

    Anthropic responses are a list of typed blocks (``text``, ``tool_use``, ...).
    ``AnthropicProvider.run`` must collect the text and lift each ``tool_use``
    block into a neutral ``ToolUse``. We verify that translation in isolation:
    """
    # ``SimpleNamespace`` mimics the SDK's block/response objects (attribute
    # access like ``block.type``) without importing or calling the real SDK.
    blocks = [SimpleNamespace(type="text", text="hi"),
              SimpleNamespace(type="tool_use", id="9", name="get_project", input={"slug": "a"})]
    fake_resp = SimpleNamespace(stop_reason="tool_use", content=blocks)

    prov = AnthropicProvider.__new__(AnthropicProvider)   # bypass __init__ (no SDK/network)
    # Inject a fake SDK client: ``messages.create(**kw)`` just returns our canned
    # response, so ``run`` exercises real translation logic against fake I/O.
    prov._client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_resp))
    prov._model, prov._max_tokens = "m", 100  # fields ``run`` reads when calling the SDK

    turn = prov.run(system="s", messages=[], tools=[])
    assert turn.text == "hi"                        # text block flattened into .text
    assert turn.tool_uses[0].name == "get_project"  # tool_use block lifted into a ToolUse
