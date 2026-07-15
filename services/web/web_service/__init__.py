"""web_service package — the browser-facing BFF (Backend For Frontend).

This package is the ONLY one of the three microservices that a human's browser
talks to directly. The other two services in this monorepo are pure back-ends:

    - content service (port 8001): owns project data (Markdown + frontmatter).
    - ai service     (port 8002): Claude-backed chat with an agentic tool loop.

``web_service`` (port 8000) owns NO data of its own. Its entire job is to be an
*orchestrator*: it renders HTML (Jinja2 + HTMX + Alpine) and, to fill that HTML
with real content, it calls the content and ai services over HTTP+JSON RPC. This
"owns the UI, borrows the data" arrangement is the classic BFF pattern.

Why keep this file (an empty ``__init__.py``) around at all? Its mere presence
marks this directory as an importable Python package, which is what lets the rest
of the code say ``from web_service.routes import ...`` and
``from .templating import templates``. There is intentionally no runtime code here
so that importing the package has zero side effects.
"""
