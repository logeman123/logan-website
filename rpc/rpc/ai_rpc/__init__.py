"""ai service contracts + typed client -- the *published RPC surface* of the ai service.

Mirror of ``content_rpc``, but for the **ai** microservice. As with content, the contracts live
here in the shared ``rpc`` library so BOTH the ai server and its callers import one definition:
the models are the single source of truth for the ``chat`` tool's request/response shape.

What's in here
--------------
* ``contracts`` -- ``ChatIn`` (the user's message going in) and ``ChatOut`` (the assistant's
  reply coming back). Intentionally tiny: the ai service's *interesting* behavior (the agentic
  tool-use loop) is server-side; the wire contract only needs the message in and the reply out.
* ``client``   -- ``AiSource`` (the capability ``Protocol``) and ``AiRpcClient`` (the concrete
  HTTP implementation). The web BFF depends on ``AiSource`` and gets an ``AiRpcClient`` injected
  by ``deps.py``; tests inject a fake that structurally satisfies the same Protocol.

A pattern worth noticing across the whole repo: the ai service's RPC surface (this ``chat`` tool)
*also* doubles as an AI/MCP tool surface, and the ai service in turn calls content's RPC tools
(``get_project``/``list_projects``) as the tools its agentic loop invokes to ground answers. So
these small contract packages describe the seams where every service plugs into every other one.
"""
