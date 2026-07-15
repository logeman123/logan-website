"""Unit tests for ``Chat`` — the agentic tool-use loop at the heart of the ai service.

Role in the system
------------------
``Chat.reply`` (in ``ai_service.chat``) implements the agent loop that grounds
answers in real data:

1. Send the conversation to the ``LLMProvider``.
2. If the model returns a ``tool_use`` turn, execute each requested tool by
   calling the content service (``get_project`` / ``list_projects``) over RPC,
   append the tool results back into the message history, and loop.
3. When the model returns an ``end_turn`` (final text), return that text.
4. A ``max_steps`` guard prevents runaway loops.

Both collaborators are injected: the ``llm`` (an ``LLMProvider``) and the
``content`` source (anything implementing the ``ContentSource`` Protocol —
here small hand-written fakes). This dependency inversion is what lets the whole
loop be tested with no model and no network.

The testing patterns
--------------------
* ``FakeLLMProvider`` is *scripted*: we hand it the exact sequence of turns the
  "model" should produce, so we can assert the loop reacts correctly (executes
  tools, survives tool errors, stops answering).
* ``FakeContent`` / ``BrokenContent`` are tiny Protocol-conforming fakes standing
  in for the content RPC client — ``BrokenContent`` raises ``ServiceError`` to
  simulate the content service being down.
* ``RecordingLLMProvider`` additionally *captures the messages* passed on every
  ``run`` call, so later tests can inspect what the loop actually appended to the
  history (the assistant tool_use message and the user tool_result blocks).
"""

from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from ai_service.chat import Chat
from ai_service.llm import FakeLLMProvider, LLMTurn, ToolUse


class FakeContent:
    """A healthy ``ContentSource`` fake returning canned projects.

    It implements the same two methods (``list_projects``/``get_project``) as the
    real ``ContentRpcClient``, so ``Chat`` accepts it via duck typing / the
    ``ContentSource`` Protocol — no network, no content service required.
    """
    def list_projects(self, featured=None):
        return [ProjectSummary(slug="a", title="A", blurb="b")]

    def get_project(self, slug):
        return Project(slug=slug, title="A", blurb="b", year=2026, role="dev", tech=["Python"])


class BrokenContent:
    """A ``ContentSource`` fake that simulates the content service being down.

    Every method raises ``ServiceError`` (the same exception the real
    ``ServiceClient`` raises when a backend is unreachable). Used to prove the
    loop degrades gracefully instead of crashing.
    """
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


def test_loop_executes_tool_then_answers():
    """The core loop: a tool_use turn triggers a real tool call, then the model's
    follow-up end_turn text is returned.

    Script = [ask for ``get_project``, then answer]. The loop must execute the
    tool against ``FakeContent`` between the two turns and return the final text.
    """
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="Logan built A."),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("tell me about A") == "Logan built A."


def test_direct_answer_no_tools():
    """When the model answers immediately (end_turn, no tools), the loop returns
    that text without ever touching the content source."""
    llm = FakeLLMProvider([LLMTurn("end_turn", text="hi")])
    assert Chat(llm=llm, content=FakeContent()).reply("hello") == "hi"


def test_tool_error_is_survived():
    """Graceful degradation: a failing tool call does NOT crash the loop.

    ``BrokenContent`` raises ``ServiceError`` when the tool runs. The loop must
    catch it, feed a safe error string back to the model as the tool result, and
    let the model produce its final answer anyway. The returned text is the
    model's follow-up, proving the exception never propagated out of ``reply``.
    """
    llm = FakeLLMProvider([
        LLMTurn("tool_use", tool_uses=[ToolUse("1", "get_project", {"slug": "a"})]),
        LLMTurn("end_turn", text="couldn't fetch that"),
    ])
    assert Chat(llm=llm, content=BrokenContent()).reply("x") == "couldn't fetch that"


def test_max_steps_guard():
    """The loop can't spin forever: ``max_steps`` bounds tool iterations.

    The script contains ONLY a tool_use turn, so the fake keeps repeating it (see
    ``FakeLLMProvider``'s "repeat last" behavior) — the model never says it's
    done. With ``max_steps=2`` the loop gives up and returns a graceful fallback
    ("couldn't ...") rather than looping indefinitely.
    """
    llm = FakeLLMProvider([LLMTurn("tool_use", tool_uses=[ToolUse("1", "list_projects", {})])])
    out = Chat(llm=llm, content=FakeContent(), max_steps=2).reply("loop")
    assert "couldn't" in out.lower()


class RecordingLLMProvider:
    """Scripted provider that records a copy of the messages it receives on each run."""

    def __init__(self, turns):
        # The scripted turns to replay, and a cursor into them.
        self._turns = list(turns)
        self._i = 0
        # ``calls[k]`` holds a snapshot of the message history as it was on the
        # k-th ``run`` — this is what lets tests inspect what the loop appended.
        self.calls = []

    def run(self, *, system, messages, tools):
        """Record the current message history, then replay the next scripted turn.

        Same keyword-only signature (``system``/``messages``/``tools``) as the
        real ``LLMProvider`` Protocol, so ``Chat`` treats it exactly like a model.
        The distinguishing behavior is the snapshot into ``self.calls``: because
        ``Chat`` mutates the ``messages`` list in place across loop iterations,
        tests need a per-call copy to later assert *what the loop had appended by
        the time of each run* (the assistant tool_use message, the user
        tool_result blocks). Returning turns with the same "repeat last" contract
        as ``FakeLLMProvider`` keeps the loop from running off the end of the script.
        """
        # Deep-ish copy each message dict so later mutations by the loop don't
        # retroactively change what we recorded for this call.
        self.calls.append([dict(m) for m in messages])
        # Replay scripted turns, sticking on the last one (same "repeat last"
        # contract as FakeLLMProvider) so the loop can't run off the script.
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return turn


def test_turn_with_text_and_tool_use():
    """A single turn can carry BOTH prose and a tool request, and the loop must
    preserve both when it appends the assistant message to the history.

    We record the messages and inspect the second ``run``'s history: the loop
    should have appended an ``assistant`` message whose content contains a
    ``text`` block (the "Let me check.") AND a ``tool_use`` block. This is the
    exact shape the Anthropic API expects when continuing an agentic exchange.
    """
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
    assert "text" in block_types       # the model's prose was preserved
    assert "tool_use" in block_types   # alongside the tool request block


def test_multiple_tool_uses_in_one_turn():
    """The loop executes several tool calls from one turn and returns one
    ``tool_result`` block per call, each keyed to its originating tool_use id.

    Script = [ask for both ``list_projects`` and ``get_project`` at once, then
    answer]. We inspect the second run's history for the ``user`` message whose
    content is a list of ``tool_result`` blocks and confirm there are two, with
    ``tool_use_id`` values matching the two requests. Correct id pairing is what
    lets the model associate each result with the call that produced it.
    """
    llm = RecordingLLMProvider([
        LLMTurn("tool_use", tool_uses=[
            ToolUse("1", "list_projects", {}),
            ToolUse("2", "get_project", {"slug": "a"}),
        ]),
        LLMTurn("end_turn", text="all done"),
    ])
    assert Chat(llm=llm, content=FakeContent()).reply("both") == "all done"

    second_call_messages = llm.calls[1]
    # Tool results come back as a single user message whose content is a list of
    # tool_result blocks (the Anthropic tool-use convention).
    user_results = next(
        m for m in second_call_messages
        if m["role"] == "user" and isinstance(m["content"], list)
    )
    tool_results = [b for b in user_results["content"] if b["type"] == "tool_result"]
    assert len(tool_results) == 2  # one result per requested tool call
    # Each result is tagged with the id of the tool_use it answers.
    assert {b["tool_use_id"] for b in tool_results} == {"1", "2"}
