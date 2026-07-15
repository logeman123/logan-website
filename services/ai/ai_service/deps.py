from functools import lru_cache

from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient

from .chat import Chat
from .config import Settings
from .llm import AnthropicProvider, FakeLLMProvider, LLMTurn


@lru_cache
def get_settings():
    return Settings()


def _build_llm(s):
    if s.llm_provider == "anthropic":
        return AnthropicProvider(api_key=s.llm_api_key, base_url=s.llm_base_url or None, model=s.llm_model)
    return FakeLLMProvider([LLMTurn("end_turn", text="Hi! Ask me about Logan's projects and work.")])


@lru_cache
def get_chat():
    s = get_settings()
    content = ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))
    return Chat(llm=_build_llm(s), content=content)
