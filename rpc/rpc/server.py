"""The RPC *server* — how a service publishes its tools over HTTP+JSON.

This is the mirror image of ``base.py``. Where the client knows the RPC *convention* for
*calling* tools, this module gives a service everything it needs to *expose* them:

  * ``ToolRegistry``      — an in-memory catalogue mapping a tool name to (handler function,
                            Pydantic input model). A service decorates its handlers with
                            ``@registry.tool("name")`` and the registry introspects each
                            handler's type hints to discover its input contract.
  * ``create_rpc_router`` — builds the FastAPI router that turns the registry into real HTTP
                            endpoints: ``GET /rpc/`` (discovery) and ``POST /rpc/<tool>``
                            (dispatch), guarded by a constant-time bearer-token check.
  * ``add_rpc_error_handler`` — installs the raise->HTTP-status mapping so any ``RPCError`` a
                            handler throws becomes a response with the right status code.

The big idea that ties the whole system together lives here: **the RPC surface doubles as the
AI/MCP tool surface.** Because ``ToolRegistry`` already knows each tool's name and its Pydantic
input schema, ``GET /rpc/`` can advertise a machine-readable tool catalogue. The ai service's
agentic loop consumes exactly that catalogue: the LLM asks to call ``get_project`` /
``list_projects``, and those calls are executed as ordinary RPC calls into the content service.
One registration mechanism, two consumers (human/service callers and the model).

The input model is the *single source of truth*. It is defined once in an ``*_rpc`` contract
module, imported by BOTH the handler here and the typed client in ``base.py``-land, and used
for validation on the way in and schema advertisement on the way out — so client and server can
never silently disagree about a tool's shape.
"""

import hmac
from typing import get_type_hints

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from rpc.exceptions import AuthError, InvalidRequest, NotFound, RPCError, ServiceError


class ToolRegistry:
    """Maps tool name -> (handler, pydantic input model). Handlers take one BaseModel arg.

    The registry is the service-local catalogue of callable tools. Each service creates one,
    registers its handlers on it with the ``@tool(...)`` decorator, and hands it to
    ``create_rpc_router`` to be published. Keeping registration (this class) separate from
    transport (the router) is itself dependency inversion: the tools know nothing about HTTP,
    and the HTTP layer knows nothing about any specific tool.

    The convention that every handler takes exactly one Pydantic ``BaseModel`` argument is what
    lets the registry treat all tools uniformly — validate the incoming payload against that
    model, then call the handler with a fully-typed object.
    """

    def __init__(self):
        # name (str) -> (handler callable, input BaseModel subclass). Populated by ``tool``.
        self._tools = {}

    def tool(self, name):
        """Decorator factory: ``@registry.tool("get_project")`` registers ``fn`` under that name.

        It introspects the handler's type hints to *derive* the input model rather than making
        the author declare it twice — the annotation on the handler's parameter IS the contract.
        This is why the one-model-argument convention is enforced here at registration time
        (fail fast on a mis-typed handler) instead of surfacing as a confusing error at runtime.
        """
        def deco(fn):
            # Resolve annotations to real classes (handles string/`from __future__` annotations).
            hints = get_type_hints(fn)
            # Drop the return annotation; what remains are the parameter annotations in order.
            params = [v for k, v in hints.items() if k != "return"]
            # Enforce the contract: exactly-one-and-first parameter must be a Pydantic model.
            # Without a valid input model we could neither validate payloads nor advertise a schema.
            if not params or not (isinstance(params[0], type) and issubclass(params[0], BaseModel)):
                raise TypeError(f"tool {name!r} handler must take a pydantic BaseModel arg")
            # Store the handler alongside the model class we will validate incoming payloads with.
            self._tools[name] = (fn, params[0])
            # Return ``fn`` unchanged so the decorated name still refers to the original handler.
            return fn
        return deco

    def names(self):
        """Return ``{tool_name: json_schema}`` — the discovery payload served at ``GET /rpc/``.

        ``model_json_schema()`` emits a standard JSON Schema for each tool's input model. This
        is precisely the shape the ai service turns into LLM/MCP tool definitions, so the same
        registry that dispatches calls also *describes* them to the model. Contract-as-schema.
        """
        return {name: model.model_json_schema() for name, (fn, model) in self._tools.items()}

    def dispatch(self, name, payload):
        """Validate ``payload`` against the named tool's model, run the handler, JSON-ify the result.

        This is the server-side counterpart to the client's ``call``: it is transport-agnostic
        (takes an already-decoded dict, returns a JSON-able value), which is what lets it be unit
        tested with no HTTP at all.
        """
        # Unknown tool name -> NotFound (HTTP 404). Symmetric with the client, where a 404 on the
        # wire is rebuilt as NotFound again.
        if name not in self._tools:
            raise NotFound(f"unknown tool: {name}")
        fn, model = self._tools[name]
        try:
            # The single source of truth in action: the raw payload is coerced/validated into the
            # tool's declared model. Any missing/mis-typed field is caught here, not in the handler.
            args = model.model_validate(payload)
        except ValidationError as exc:
            # Validation failure -> InvalidRequest (HTTP 400): the request was understood but bad.
            raise InvalidRequest(str(exc)) from exc
        # Handlers are synchronous by design (our httpx and Anthropic clients are sync).
        # Run the handler with the typed args, then normalise its return value to JSON-safe data.
        return _to_jsonable(fn(args))


def _to_jsonable(result):
    """Recursively convert a handler's return value into JSON-serialisable primitives.

    Handlers return rich domain objects — the shared Pydantic contract models (single or in a
    list). FastAPI can serialise many of these, but we normalise explicitly so the RPC layer's
    output is predictable regardless of what a handler hands back: models become dicts, lists are
    mapped element-wise, and anything already primitive passes straight through.
    """
    if isinstance(result, BaseModel):
        # ``mode="json"`` ensures nested exotic types (datetimes, enums, ...) become JSON-native.
        return result.model_dump(mode="json")
    if isinstance(result, list):
        # Handle list-returning tools (e.g. ``list_projects``) by converting each element.
        return [_to_jsonable(x) for x in result]
    # Already a str/int/dict/None/etc. — nothing to convert.
    return result


def create_rpc_router(registry, expected_token):
    """Build the FastAPI router that publishes ``registry`` at ``GET /rpc/`` and ``POST /rpc/<tool>``.

    ``expected_token`` is the shared secret this service will accept as its bearer token — the
    server-side half of the auth injected on the client via its ``token_provider``. Keeping the
    token a parameter (rather than reading global config here) keeps this function pure and easy
    to test with a throwaway token.
    """
    router = APIRouter()

    def _check(authorization):
        # Constant-time comparison via ``hmac.compare_digest``: a naive ``==`` on secrets can leak
        # information through *how long* it takes to fail (it short-circuits at the first mismatched
        # byte), enabling a timing attack that recovers the token character by character.
        # ``compare_digest`` always examines the full length, so failure time is independent of how
        # much of the token was correct.
        if not hmac.compare_digest(authorization, f"Bearer {expected_token}"):
            # Reuse the shared vocabulary: AuthError carries status_code 401, mapped below.
            raise AuthError("missing or invalid credentials")

    @router.get("/rpc/")
    def list_tools(authorization: str = Header(default="")):
        # Discovery is authenticated too — the tool catalogue is not public. ``default=""`` means a
        # missing header becomes an empty string that simply fails the check (rather than erroring).
        _check(authorization)
        # Hand back the {name: json_schema} map — the surface the AI/MCP layer consumes.
        return registry.names()

    @router.post("/rpc/{tool}")
    async def call_tool(tool: str, request: Request, authorization: str = Header(default="")):
        # Authenticate before doing any work, including before reading the body.
        _check(authorization)
        # Read the raw body ourselves so an empty POST is legal: a no-argument tool can be called
        # with no body at all, which we treat as an empty ``{}`` payload rather than a JSON error.
        body = await request.body()
        payload = await request.json() if body else {}
        try:
            # Delegate to the transport-agnostic dispatcher; it validates and runs the handler.
            return registry.dispatch(tool, payload)
        except RPCError:
            # Already-classified errors (NotFound, InvalidRequest, or anything a handler raised on
            # purpose) pass through untouched so the error handler can map their status codes.
            raise
        except Exception as exc:  # unexpected handler failure -> 500
            # A handler bug or unforeseen exception is contained here and normalised to ServiceError
            # (500) — the client will rebuild it as ServiceError too, so callers degrade gracefully
            # instead of seeing a raw stack trace or an unhandled 500 with no ``detail``.
            raise ServiceError(str(exc)) from exc

    return router


def add_rpc_error_handler(app):
    """Register the app-wide handler that turns any ``RPCError`` into a JSON response.

    This is the raise->HTTP-status half of the symmetric mapping. Every ``RPCError`` subclass
    carries the correct ``status_code`` (400/401/404/500), so this one handler serves all of
    them without a big if/else — the exception classes ARE the routing table. On the client
    side, ``error_for_status`` performs the exact inverse, completing the round-trip.
    """
    @app.exception_handler(RPCError)
    async def _handle(request, exc):
        # Status comes straight off the exception's class attribute; the message becomes ``detail``,
        # the same field the client reads back when reconstructing the error.
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
