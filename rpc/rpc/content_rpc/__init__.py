"""content service contracts + typed client -- the *published RPC surface* of content.

Big picture
-----------
This package is the shared, importable "API definition" for the **content** microservice.
It lives inside the ``rpc`` shared library (not inside the content service itself) on purpose:
in this codebase the contracts are the **single source of truth** that BOTH sides import.

  * The content *server* imports these Pydantic models to validate what it returns.
  * Every *caller* (the web BFF, and indirectly the ai service's tool loop) imports the SAME
    models to parse the responses it receives.

Because both ends share one definition, the wire format cannot silently drift: if the server
changes a field, the callers recompile against the new shape. This is how you get "typed RPC"
without a heavyweight IDL/codegen step (like gRPC/protobuf) -- plain Pydantic classes act as
the interface description language.

What's in here
--------------
* ``contracts`` -- the Pydantic request/response models (``ProjectSummary``, ``Project``,
  ``ListProjectsIn``, ``GetProjectIn``). These describe *data*, not behavior.
* ``client``   -- ``ContentSource`` (a structural ``Protocol`` describing the *capability*)
  and ``ContentRpcClient`` (a concrete implementation that talks HTTP via ``ServiceClient``).

Why a Protocol + a client? -- dependency inversion
--------------------------------------------------
Callers depend on the ``ContentSource`` Protocol (an abstraction), never on ``ContentRpcClient``
(a concrete detail). At runtime ``deps.py`` in the web service injects a real ``ContentRpcClient``;
in tests an in-memory fake that structurally satisfies the same Protocol is injected instead.
Neither the caller's code nor its type checks change -- that is dependency inversion at work.
"""
