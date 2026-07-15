"""Unit tests for the content service's repository layer.

Role in the system
------------------
The content service "owns" the project data for the whole site. It hides the
storage mechanism behind a ``ContentRepository`` *Protocol* (structural
interface) so the rest of the service never depends on *where* projects come
from. Two concrete implementations satisfy that Protocol:

* ``FileContentRepository`` -- the real one, reading Markdown + YAML
  frontmatter files from ``content_service/data/projects/``.
* ``InMemoryContentRepository`` -- a test fake holding pre-built ``Project``
  objects in a list.

Because both implementations honor the same Protocol, this module can prove
they behave *identically* by running every behavioral test against BOTH via a
single parametrized fixture (see ``repo`` below). This is the payoff of
dependency inversion: the tests target the interface, not a class, so the file
backend and the in-memory fake are interchangeable and provably equivalent.

These are pure unit tests: no HTTP, no network, no RPC. They exercise the
repository objects directly. The RPC surface that wraps this repository is
tested separately in ``test_content_app.py``.
"""

import pytest
from rpc.content_rpc.contracts import Project
from rpc.exceptions import NotFound
from content_service.repository import FileContentRepository, InMemoryContentRepository

# Absolute path to the real project data directory. ``parents[1]`` climbs from
# this file (services/content/tests/) up to services/content/, then we descend
# into the package's bundled data. Using __import__("pathlib") inline avoids a
# top-level pathlib import purely to compute one constant.
DATA = __import__("pathlib").Path(__file__).parents[1] / "content_service" / "data" / "projects"


@pytest.fixture(params=["file", "memory"])
def repo(request):
    """Yield each ContentRepository implementation in turn (file, then memory).

    This is the key testing pattern for this module. ``params=["file",
    "memory"]`` makes pytest run every test that depends on ``repo`` TWICE --
    once per param -- so a single test body validates both backends. Any test
    passing here is a guarantee that the file backend and the in-memory fake are
    behaviorally interchangeable, which is exactly what the Protocol promises.
    """
    if request.param == "file":
        # The real backend, pointed at the on-disk Markdown project files.
        return FileContentRepository(DATA)
    # For the "memory" param we seed the fake with data produced BY the file
    # backend, so both variants operate over the identical set of projects.
    # ``list_projects`` returns lightweight summaries, so we re-fetch each full
    # ``Project`` (with rendered body) by slug to hydrate the in-memory store.
    projects = FileContentRepository(DATA).list_projects()
    full = [FileContentRepository(DATA).project(p.slug) for p in projects]
    return InMemoryContentRepository(full)


def test_list_all(repo):
    # Both backends must surface the known "this-website" project. Note this
    # single assertion runs for BOTH the file and memory params of ``repo``.
    slugs = {p.slug for p in repo.list_projects()}
    assert "this-website" in slugs


def test_featured_filter(repo):
    # The optional ``featured`` filter must (a) return only featured projects
    # and (b) still include the known-featured "this-website". Verifying the
    # filter logic lives in the repo -- not in the caller -- keeps the RPC/web
    # layers thin.
    featured = repo.list_projects(featured=True)
    assert all(p.featured for p in featured)
    assert any(p.slug == "this-website" for p in featured)


def test_get_project_renders_body(repo):
    # A full ``Project`` must come back with its Markdown body already rendered
    # to HTML. Rendering happens inside the repository so every caller (RPC, AI
    # grounding, web templates) receives ready-to-display HTML.
    p = repo.project("this-website")
    assert isinstance(p, Project)
    assert "<" in p.body_html  # presence of a tag proves markdown was rendered to HTML


def test_missing_raises(repo):
    # Requesting an unknown slug must raise the domain error ``NotFound`` (from
    # the shared rpc.exceptions hierarchy). The RPC error handler later maps
    # this exact exception type to an HTTP 404, so raising it here is what makes
    # correct status codes possible upstream without the repo knowing about HTTP.
    with pytest.raises(NotFound):
        repo.project("does-not-exist")


def test_malformed_file_is_skipped(tmp_path):
    # Per-file error isolation: one broken Markdown file must NOT take down the
    # whole listing. We write one valid file and one that violates the Project
    # contract, then assert only the valid one survives.
    (tmp_path / "good.md").write_text(
        "---\nslug: good\ntitle: Good Project\n---\nA valid body.\n"
    )
    # tech must be a list; a string triggers a pydantic ValidationError on construct.
    # FileContentRepository is expected to catch that per-file and skip the file
    # rather than propagate the error and break list_projects for everyone.
    (tmp_path / "bad.md").write_text(
        "---\nslug: bad\ntitle: Bad Project\ntech: not-a-list\n---\nOops.\n"
    )
    # ``tmp_path`` is pytest's per-test temp dir fixture, giving us a throwaway
    # data directory so we can point a real FileContentRepository at fixtures we
    # control (no need to touch the bundled data files).
    repo = FileContentRepository(tmp_path)
    projects = repo.list_projects()
    assert {p.slug for p in projects} == {"good"}


def test_missing_optional_fields_default(tmp_path):
    # A minimal frontmatter (only the required slug + title) must still produce
    # a valid Project, with every optional field falling back to its declared
    # default. Those defaults are defined once on the pydantic contract in
    # rpc.content_rpc.contracts, so the whole system agrees on what "empty" means.
    (tmp_path / "minimal.md").write_text(
        "---\nslug: minimal\ntitle: Minimal Project\n---\nJust a body.\n"
    )
    repo = FileContentRepository(tmp_path)
    p = repo.project("minimal")
    assert isinstance(p, Project)
    assert p.tech == []          # list-typed default
    assert p.featured is False   # boolean default
    assert p.year is None        # optional scalar default
    assert p.highlights == []    # list-typed default
    assert p.links == {}         # dict-typed default
