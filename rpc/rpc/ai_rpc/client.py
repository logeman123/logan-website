from typing import Protocol

from rpc.base import ServiceClient

from .contracts import ChatOut


class AiSource(Protocol):
    def chat(self, message: str) -> ChatOut: ...


class AiRpcClient:
    def __init__(self, client: ServiceClient):
        self._c = client

    def chat(self, message):
        return ChatOut.model_validate(self._c.call("chat", message=message))
