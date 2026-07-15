"""The agentic tool-use loop — the "brain stem" of the ai service.

``Chat.reply`` orchestrates a multi-turn conversation between the model and the content
service until the model produces a final answer. This is the classic **agentic tool-use
loop**:

    1. Ask the model, giving it the system prompt, the running transcript, and the tools.
    2. If the model is DONE (stop_reason != "tool_use"), return its text — that's the answer.
    3. If the model wants tools, run each requested tool (grounding on real content data),
       append both the model's tool-call request AND the tool results to the transcript,
       then loop back to step 1 so the model can use those results.
    4. Guard the loop with ``max_steps`` so a misbehaving model can't spin forever.

Everything ``Chat`` touches is injected as a Protocol: the model is an ``LLMProvider`` and
the data source is a ``ContentSource``. So this class is completely decoupled from both the
Anthropic SDK and the HTTP transport — in tests it drives a FakeLLMProvider against an
in-memory content fake and never touches the network, yet the exact same code path runs in
production against real Claude and the real content service.
"""

from rpc.content_rpc.client import ContentSource

from .llm import LLMProvider
from .tools import TOOL_SPECS, execute_tool

# The system prompt: sets the assistant's persona and — importantly — instructs it to use
# the tools to fetch REAL data rather than guessing. This is the prose half of grounding;
# TOOL_SPECS is the machine-readable half.
SYSTEM = (
    "You are the assistant on Logan Schwappach's personal website. "
    "Answer questions about Logan, his projects, and his work, using the tools to fetch real data "
    "rather than guessing. If asked something unrelated, briefly steer back to Logan's work."
)


class Chat:
    """Runs one user message through the agentic tool-use loop and returns a final reply.

    Collaborators are injected (dependency inversion), never constructed here:
    * ``llm``     — any ``LLMProvider`` (real AnthropicProvider or FakeLLMProvider).
    * ``content`` — any ``ContentSource`` (real ContentRpcClient or an in-memory fake),
                    passed straight through to ``execute_tool`` for grounding.
    * ``max_steps`` — hard cap on model round-trips, so the loop always terminates.

    The composition of these concretes happens in deps.py; rpc_tools.py then exposes
    ``reply`` as the RPC/AI tool named "chat".
    """

    def __init__(self, *, llm: LLMProvider, content: ContentSource, max_steps: int = 5):
        self._llm = llm
        self._content = content
        self._max_steps = max_steps

    def reply(self, message: str) -> str:
        # ``messages`` is the growing conversation transcript in Anthropic's message format.
        # It starts with just the user's question and accumulates assistant/tool turns as
        # the loop iterates.
        messages = [{"role": "user", "content": message}]
        for _ in range(self._max_steps):
            # Step 1: invoke the model with the current transcript and the tool catalog.
            turn = self._llm.run(system=SYSTEM, messages=messages, tools=TOOL_SPECS)
            # Step 2: if the model did NOT ask for tools, this turn's text IS the answer.
            if turn.stop_reason != "tool_use":
                return turn.text
            # Step 3a: reconstruct the assistant's turn as content blocks so we can append it
            # to the transcript. The API requires the assistant's tool_use blocks to be
            # present in history before we're allowed to send back matching tool_result blocks.
            assistant = []
            if turn.text:
                # Preserve any prose the model emitted alongside its tool calls.
                assistant.append({"type": "text", "text": turn.text})
            for tu in turn.tool_uses:
                # Echo each tool-call request back into history verbatim (id is the pairing key).
                assistant.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
            messages.append({"role": "assistant", "content": assistant})
            # Step 3b: actually execute every requested tool. execute_tool performs the
            # ai -> content RPC hop and NEVER raises (errors come back as strings), so one
            # failing tool can't break the loop. Each result is tagged with tool_use_id so
            # the model can match each answer to the request that produced it.
            results = [
                {"type": "tool_result", "tool_use_id": tu.id,
                 "content": execute_tool(self._content, tu.name, tu.input)}
                for tu in turn.tool_uses
            ]
            # Tool results are delivered back to the model as a "user"-role message (that's
            # the Anthropic convention). Then the for-loop iterates: the model now sees the
            # grounding data and can answer or request more tools.
            messages.append({"role": "user", "content": results})
        # Step 4: we exhausted max_steps without the model ever finishing. Fail safe with a
        # friendly message rather than looping forever or raising.
        return "Sorry — I couldn't complete that request."
