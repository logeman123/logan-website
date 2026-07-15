"""routes package — one module per group of URL endpoints for the web BFF.

Each sibling module (``home``, ``work``, ``chat``, ``resume``) defines a FastAPI
``APIRouter`` holding the endpoints for one area of the site. ``main.py`` imports
these modules and calls ``app.include_router(...)`` on each, which is how the
individual routers get stitched together into the single running application.

Splitting routes across modules (instead of hanging every endpoint off one big
``app``) keeps each concern isolated and makes the dependency-injection wiring
easy to follow: the data-backed routes (``work``, ``chat``) declare exactly which
RPC client they need via ``Depends(...)``, while the static routes (``home``,
``resume``) declare none.

This file is intentionally empty apart from this docstring — it exists only to
make ``routes`` an importable Python sub-package.
"""
