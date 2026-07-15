from functools import lru_cache

from rpc.ai_rpc.client import AiRpcClient, AiSource
from rpc.base import ServiceClient, static_token_provider
from rpc.content_rpc.client import ContentRpcClient, ContentSource

from .config import Settings


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_content() -> ContentSource:
    s = get_settings()
    return ContentRpcClient(ServiceClient(s.content_url, static_token_provider(s.service_token)))


@lru_cache
def get_ai() -> AiSource:
    s = get_settings()
    return AiRpcClient(ServiceClient(s.ai_url, static_token_provider(s.service_token)))
