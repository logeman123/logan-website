from typing import Protocol

from rpc.base import ServiceClient

from .contracts import Project, ProjectSummary


class ContentSource(Protocol):
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    def get_project(self, slug: str) -> Project: ...


class ContentRpcClient:
    def __init__(self, client: ServiceClient):
        self._c = client

    def list_projects(self, featured=None):
        rows = self._c.call("list_projects", featured=featured)
        return [ProjectSummary.model_validate(r) for r in rows]

    def get_project(self, slug):
        return Project.model_validate(self._c.call("get_project", slug=slug))
