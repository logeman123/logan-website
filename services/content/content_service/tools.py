from rpc.content_rpc.contracts import GetProjectIn, ListProjectsIn, Project, ProjectSummary
from rpc.server import ToolRegistry

from .repository import ContentRepository


def build_content_registry(repo: ContentRepository) -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool("list_projects")
    def list_projects(args: ListProjectsIn) -> list[ProjectSummary]:
        return repo.list_projects(featured=args.featured)

    @reg.tool("get_project")
    def get_project(args: GetProjectIn) -> Project:
        return repo.project(args.slug)

    return reg
