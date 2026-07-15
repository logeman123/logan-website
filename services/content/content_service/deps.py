from functools import lru_cache

from .config import Settings
from .repository import FileContentRepository


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_repository():
    return FileContentRepository(get_settings().data_dir)
