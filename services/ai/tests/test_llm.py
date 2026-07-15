from types import SimpleNamespace
from ai_service.llm import AnthropicProvider, FakeLLMProvider, LLMTurn, ToolUse


def test_fake_returns_scripted_then_repeats():
    p = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
                         LLMTurn("end_turn", text="done")])
    assert p.run(system="s", messages=[], tools=[]).stop_reason == "tool_use"
    assert p.run(system="s", messages=[], tools=[]).text == "done"
    assert p.run(system="s", messages=[], tools=[]).text == "done"  # repeats last


def test_anthropic_maps_blocks(monkeypatch):
    blocks = [SimpleNamespace(type="text", text="hi"),
              SimpleNamespace(type="tool_use", id="9", name="get_project", input={"slug": "a"})]
    fake_resp = SimpleNamespace(stop_reason="tool_use", content=blocks)

    prov = AnthropicProvider.__new__(AnthropicProvider)   # bypass __init__ (no SDK/network)
    prov._client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_resp))
    prov._model, prov._max_tokens = "m", 100

    turn = prov.run(system="s", messages=[], tools=[])
    assert turn.text == "hi"
    assert turn.tool_uses[0].name == "get_project"
