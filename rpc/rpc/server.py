import hmac
from typing import get_type_hints

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from rpc.exceptions import AuthError, InvalidRequest, NotFound, RPCError, ServiceError


class ToolRegistry:
    """Maps tool name -> (handler, pydantic input model). Handlers take one BaseModel arg."""

    def __init__(self):
        self._tools = {}

    def tool(self, name):
        def deco(fn):
            hints = get_type_hints(fn)
            params = [v for k, v in hints.items() if k != "return"]
            if not params or not (isinstance(params[0], type) and issubclass(params[0], BaseModel)):
                raise TypeError(f"tool {name!r} handler must take a pydantic BaseModel arg")
            self._tools[name] = (fn, params[0])
            return fn
        return deco

    def names(self):
        return {name: model.model_json_schema() for name, (fn, model) in self._tools.items()}

    def dispatch(self, name, payload):
        if name not in self._tools:
            raise NotFound(f"unknown tool: {name}")
        fn, model = self._tools[name]
        try:
            args = model.model_validate(payload)
        except ValidationError as exc:
            raise InvalidRequest(str(exc)) from exc
        # Handlers are synchronous by design (our httpx and Anthropic clients are sync).
        return _to_jsonable(fn(args))


def _to_jsonable(result):
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_to_jsonable(x) for x in result]
    return result


def create_rpc_router(registry, expected_token):
    router = APIRouter()

    def _check(authorization):
        if not hmac.compare_digest(authorization, f"Bearer {expected_token}"):
            raise AuthError("missing or invalid credentials")

    @router.get("/rpc/")
    def list_tools(authorization: str = Header(default="")):
        _check(authorization)
        return registry.names()

    @router.post("/rpc/{tool}")
    async def call_tool(tool: str, request: Request, authorization: str = Header(default="")):
        _check(authorization)
        body = await request.body()
        payload = await request.json() if body else {}
        try:
            return registry.dispatch(tool, payload)
        except RPCError:
            raise
        except Exception as exc:  # unexpected handler failure -> 500
            raise ServiceError(str(exc)) from exc

    return router


def add_rpc_error_handler(app):
    @app.exception_handler(RPCError)
    async def _handle(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})
