"""Composition root — the ONE place the content service names concrete classes.

Everywhere else in this service depends on *abstractions*: ``tools.py`` takes a
``ContentRepository`` Protocol, ``main.py`` takes whatever ``get_repository()``
returns. This module is where those abstractions get bound to real
implementations — the "composition root" of the dependency-injection design.
Keeping that choice in a single file means:

  * to swap the data source (files -> database, or the in-memory fake in a test),
    you change it here and nowhere else;
  * the rest of the code stays testable and ignorant of concrete types.

Both providers are wrapped in ``functools.lru_cache`` so they behave as lazy
singletons: the first call constructs the object, every later call returns the
exact same instance. That is the caching decision the repository deliberately
left OUT of itself — one Settings object and one repository per process.
"""

from functools import lru_cache

from .config import Settings
from .repository import FileContentRepository


@lru_cache
def get_settings():
    """Return the process-wide ``Settings`` instance (constructed once, cached).

    ``lru_cache`` makes this a lazy singleton: Settings reads the environment /
    ``.env`` exactly once, on first call, and hands back the same object
    thereafter — so config isn't re-parsed on every request.
    """
    return Settings()


@lru_cache
def get_repository():
    """Return the concrete repository the service will use (cached singleton).

    THIS is the injection point. Production wires in ``FileContentRepository``,
    pointed at the ``data_dir`` from settings. A test swaps in an
    ``InMemoryContentRepository`` instead — nothing downstream changes, because
    everything downstream only knows the ``ContentRepository`` Protocol.

    Caching here (rather than in the repository) means one repository instance
    per process, while the repo itself still re-reads files on each ``_load()``
    call so content edits remain visible without a restart.
    """
    return FileContentRepository(get_settings().data_dir)
