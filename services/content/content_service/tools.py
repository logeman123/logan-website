"""Exposes the content repository as RPC tools — the service's public surface.

This module is the bridge between the private data layer (``repository.py``) and
the outside world. It registers two named tools on a ``ToolRegistry``:

    list_projects  ->  POST /rpc/list_projects
    get_project    ->  POST /rpc/get_project

The shared ``rpc`` library (see ``rpc.server`` and how ``main.py`` mounts it)
turns that registry into real HTTP endpoints and a discovery listing at
``GET /rpc/``. Each registered tool is a plain function whose *typed* input and
output are the Pydantic contracts from ``rpc/content_rpc`` — the framework
validates the request body into the input model and serializes the returned
model back to JSON, so this code deals only in well-typed Python objects.

A key architectural insight of the whole project: **this RPC surface doubles as
the AI tool surface.** The ``ai`` service's agentic tool-use loop calls these
very same ``get_project`` / ``list_projects`` tools (over RPC) to ground its
chat answers in real data. One definition, two consumers.
"""

from rpc.content_rpc.contracts import GetProjectIn, ListProjectsIn, Project, ProjectSummary
from rpc.server import ToolRegistry

# Imported for the type annotation on `repo` below. Depending on the Protocol
# (not a concrete class) is the whole point: these tools never know or care
# whether the data comes from files or memory.
from .repository import ContentRepository


def build_content_registry(repo: ContentRepository) -> ToolRegistry:
    """Build and return a ToolRegistry with the repo *injected* into each tool.

    This is a small **dependency-injection factory**. It takes any object that
    satisfies the ``ContentRepository`` Protocol and produces a registry of RPC
    tools that close over it. Because the repository arrives as an argument
    (rather than being constructed in here), the caller decides the data source:
    ``deps.py`` passes the file-backed repo in production, while tests pass an
    ``InMemoryContentRepository``. The tool logic below is identical either way.

    The registry itself is data — a dict of {name -> typed handler} — and does
    no HTTP. ``main.py`` hands it to ``create_rpc_router`` to become endpoints.
    """
    reg = ToolRegistry()

    # `@reg.tool("name")` registers the function under that public tool name and
    # records its input/output types (from the annotations) for validation and
    # for the self-describing GET /rpc/ listing. The nested functions close over
    # `repo`, which is how the injected dependency reaches the handler.
    @reg.tool("list_projects")
    def list_projects(args: ListProjectsIn) -> list[ProjectSummary]:
        # `args` has already been parsed/validated from the request JSON into the
        # ListProjectsIn contract by the framework. We just delegate to the repo.
        return repo.list_projects(featured=args.featured)

    @reg.tool("get_project")
    def get_project(args: GetProjectIn) -> Project:
        # Delegate to the repo; if the slug is unknown the repo raises NotFound,
        # which the shared error handler maps to HTTP 404 for the caller.
        return repo.project(args.slug)

    return reg
