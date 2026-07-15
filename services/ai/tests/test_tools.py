"""Unit tests for ``execute_tool`` — the ai service's tool dispatcher.

Role in the system
------------------
``execute_tool(content, name, args)`` (in ``ai_service.tools``) is the bridge
between the model's tool requests and the content service. Given a tool ``name``
and its ``args`` dict, it calls the matching method on the injected ``content``
source and renders the result as a **plain string** suitable for feeding back to
the model as a ``tool_result``. Crucially, it is designed to NEVER raise: every
failure mode (unknown tool, missing argument, backend down) is converted into a
safe descriptive string. That contract is what keeps the agentic loop in
``Chat`` robust — a bad tool call becomes text the model can react to, not an
exception that aborts the request.

The testing pattern
-------------------
Same Protocol-fake approach as the chat tests. Several tiny ``*Content`` fakes
each represent one scenario (healthy, empty, broken), letting each test target
exactly one rendering/degradation branch of ``execute_tool`` with no network.
"""

from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import ServiceError
from ai_service.tools import execute_tool


class FakeContent:
    """Healthy content fake: returns one project for both tools."""
    def list_projects(self, featured=None):
        return [ProjectSummary(slug="a", title="Alpha", blurb="first")]

    def get_project(self, slug):
        return Project(slug=slug, title="Alpha", blurb="first", year=2026, role="dev", tech=["Python"])


class EmptyContent:
    """Content fake with no projects — exercises the empty-list rendering.

    ``get_project`` asserts it is never called, documenting that the empty-list
    test only touches ``list_projects``.
    """
    def list_projects(self, featured=None):
        return []

    def get_project(self, slug):
        raise AssertionError("not expected")


class BrokenContent:
    """Content fake that simulates the backend being unreachable (raises
    ``ServiceError``) — exercises the graceful-degradation branch."""
    def list_projects(self, featured=None):
        raise ServiceError("down")

    def get_project(self, slug):
        raise ServiceError("down")


def test_get_project_success_contains_title():
    """A successful ``get_project`` renders the project's title into the string."""
    out = execute_tool(FakeContent(), "get_project", {"slug": "a"})
    assert "Alpha" in out


def test_list_projects_with_results_contains_slug_and_title():
    """A successful ``list_projects`` renders each project's slug and title so the
    model has enough grounding to reference specific projects."""
    out = execute_tool(FakeContent(), "list_projects", {})
    assert "a" in out
    assert "Alpha" in out


def test_list_projects_empty_returns_no_projects_found():
    """An empty result set renders a clear sentinel string rather than "" so the
    model isn't confused by a blank tool result."""
    assert execute_tool(EmptyContent(), "list_projects", {}) == "No projects found."


def test_unknown_tool_name():
    """An unrecognized tool name returns a descriptive string (never raises), so
    a hallucinated tool call can't break the loop."""
    assert execute_tool(FakeContent(), "bogus", {}) == "Unknown tool: bogus"


def test_rpc_error_returns_safe_string_and_does_not_raise():
    """A backend failure (``ServiceError``) is caught and turned into a safe
    "(tool error fetching content: ...)" string.

    This is the tool-level side of graceful degradation: the content service
    being down surfaces to the model as readable text, letting the chat loop
    (see ``test_tool_error_is_survived``) still produce an answer.
    """
    out = execute_tool(BrokenContent(), "get_project", {"slug": "a"})
    assert out.startswith("(tool error fetching content:")


def test_get_project_missing_slug_returns_safe_string():
    """Malformed args (missing required ``slug``) also return a safe string.

    The model sometimes emits incomplete tool inputs; ``execute_tool`` validates
    and reports the problem as text instead of raising a ``KeyError``.
    """
    out = execute_tool(FakeContent(), "get_project", {})
    assert out == "(tool error: missing required argument 'slug')"
