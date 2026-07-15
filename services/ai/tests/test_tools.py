from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from ai_service.tools import execute_tool


class FakeContent:
    def list_projects(self, featured=None):
        return [ProjectSummary(slug="a", title="Alpha", blurb="first")]

    def get_project(self, slug):
        return Project(slug=slug, title="Alpha", blurb="first", year=2026, role="dev", tech=["Python"])


class EmptyContent:
    def list_projects(self, featured=None):
        return []

    def get_project(self, slug):
        raise AssertionError("not expected")


class BrokenContent:
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


def test_get_project_success_contains_title():
    out = execute_tool(FakeContent(), "get_project", {"slug": "a"})
    assert "Alpha" in out


def test_list_projects_with_results_contains_slug_and_title():
    out = execute_tool(FakeContent(), "list_projects", {})
    assert "a" in out
    assert "Alpha" in out


def test_list_projects_empty_returns_no_projects_found():
    assert execute_tool(EmptyContent(), "list_projects", {}) == "No projects found."


def test_unknown_tool_name():
    assert execute_tool(FakeContent(), "bogus", {}) == "Unknown tool: bogus"


def test_rpc_error_returns_safe_string_and_does_not_raise():
    out = execute_tool(BrokenContent(), "get_project", {"slug": "a"})
    assert out.startswith("(tool error fetching content:")


def test_get_project_missing_slug_returns_safe_string():
    out = execute_tool(FakeContent(), "get_project", {})
    assert out == "(tool error: missing required argument 'slug')"
