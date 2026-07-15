from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn, ToolUse


class FakeContent:
    def list_projects(self, featured=None):
        return [ProjectSummary(slug="a", title="A", blurb="b")]

    def get_project(self, slug):
        return Project(slug=slug, title="A", blurb="b", year=2026, role="dev", tech=["Python"])


class BrokenContent:
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


def test_loop_executes_tool_then_answers():
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="Logan built A."),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("tell me about A") == "Logan built A."


def test_direct_answer_no_tools():
    llm = FakeLLMProvider([LLMTurn("end_turn", text="hi")])
    assert Chat(llm=llm, content=FakeContent()).reply("hello") == "hi"


def test_tool_error_is_survived():
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="couldn't fetch that"),
    ])
    assert Chat(llm=llm, content=BrokenContent()).reply("x") == "couldn't fetch that"


def test_max_steps_guard():
    llm = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "list_projects", {})])])
    out = Chat(llm=llm, content=FakeContent(), max_steps=2).reply("loop")
    assert "couldn't" in out.lower()


class RecordingLLMProvider:
    """Scripted provider that records a copy of the messages it receives on each run."""

    def __init__(self, turns):
        self._turns = list(turns)
        self._i = 0
        self.calls = []

    def run(self, *, system, messages, tools):
        self.calls.append([dict(m) for m in messages])
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return turn


def test_turn_with_text_and_tool_use():
    llm = RecordingLLMProvider([
        LLMTurn("tool_use", text="Let me check.",
                tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="done"),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("tell me about A") == "done"

    # On the second run the loop must have appended the assistant tool_use message.
    second_call_messages = llm.calls[1]
    assistant = next(m for m in second_call_messages if m["role"] == "assistant")
    block_types = {b["type"] for b in assistant["content"]}
    assert "text" in block_types
    assert "tool_use" in block_types


def test_multiple_tool_uses_in_one_turn():
    llm = RecordingLLMProvider([
        LLMTurn("tool_use", tool_uses=[
            ToolUse("1", "list_projects", {}),
            ToolUse("2", "get_project", {"slug": "a"}),
        ]),
        LLMTurn("end_turn", text="all done"),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("both") == "all done"

    second_call_messages = llm.calls[1]
    user_results = next(
        m for m in second_call_messages
        if m["role"] == "user" and isinstance(m["content"], list)
    )
    tool_results = [b for b in user_results["content"] if b["type"] == "tool_result"]
    assert len(tool_results) == 2
    assert {b["tool_use_id"] for b in tool_results} == {"1", "2"}
