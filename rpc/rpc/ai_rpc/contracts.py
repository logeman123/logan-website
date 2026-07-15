"""Pydantic data contracts for the **ai** service's RPC surface (the ``chat`` tool).

These two models are the entire wire schema for the ai service, and -- like all contracts in the
``rpc`` package -- they are imported by BOTH the ai server (which validates what it returns) and
the callers (which parse the reply). One definition, no drift.

Note how minimal this is. All the complexity of the ai service -- the agentic tool-use loop where
the model requests tool calls, the loop executes them against content's ``get_project`` /
``list_projects`` RPC tools to ground the answer, then feeds the results back for another turn --
happens *behind* this contract. From a caller's perspective the ai service is a black box: send
one ``message``, receive one ``reply``. Keeping the contract this thin means the loop's internals
can change freely without ever breaking a caller.
"""

from pydantic import BaseModel


class ChatIn(BaseModel):
    """Typed arguments for the ``chat`` RPC tool -- just the user's message going in.

    Wrapping the single field in a model (rather than passing a bare string) keeps every RPC tool
    uniform: one validated request object per tool, and room to add fields (history, options)
    later without changing the call signature.
    """

    message: str  # The end user's chat prompt; forwarded into the ai service's tool-use loop.


class ChatOut(BaseModel):
    """Typed result of the ``chat`` RPC tool -- the assistant's final reply text.

    This is what the tool-use loop returns *after* it has finished any grounding tool calls to
    the content service. The web BFF renders it into the chat partial; if the ai service is
    unreachable the BFF catches the RPCError instead and shows a fallback (graceful degradation).
    """

    reply: str  # The model's final natural-language answer, already grounded by any tool calls.
