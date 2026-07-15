"""Package marker for the **ai** microservice's Python package (``ai_service``).

Where this sits in the overall system
-------------------------------------
This project is a monorepo of THREE independent FastAPI microservices that talk to
each other over HTTP + JSON (a tiny "RPC" convention defined in the shared ``rpc``
library):

    web  (BFF, port 8000)  ── calls ──▶  ai  (port 8002)  ── calls ──▶  content (port 8001)

* ``content`` owns the data (Logan's projects, read from Markdown files).
* ``ai`` (THIS service) is the Claude-backed "brain": it answers chat questions and
  grounds its answers by calling ``content``'s RPC tools instead of hallucinating.
* ``web`` is the browser-facing app that orchestrates the other two but owns no data.

The presence of this ``__init__.py`` is what makes ``ai_service`` an importable Python
package, so sibling modules can use *relative* imports like ``from .chat import Chat``
and ``from .config import Settings``. It is intentionally empty of runtime code: the
real entrypoint is ``ai_service.main:app`` (the FastAPI application), and the wiring
(dependency injection) lives in ``ai_service.deps``.

Reading order for someone new to this service:
    config.py     -> environment-driven settings (which LLM, which content URL, ...)
    llm.py        -> the LLMProvider Protocol + real/fake implementations
    tools.py      -> the tools the model may call, and how they ground on content RPC
    chat.py       -> the agentic tool-use loop that drives the model
    rpc_tools.py  -> exposes Chat.reply as an RPC "tool" named "chat"
    deps.py       -> composition root: constructs and wires the concrete objects
    main.py       -> builds the FastAPI app and mounts the RPC router
"""
