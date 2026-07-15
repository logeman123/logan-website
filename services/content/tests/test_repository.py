import pytest
from rpc.content_rpc.contracts import Project
from rpc.exceptions import NotFound
from content_service.repository import FileContentRepository, InMemoryContentRepository

DATA = __import__("pathlib").Path(__file__).parents[1] / "content_service" / "data" / "projects"


@pytest.fixture(params=["file", "memory"])
def repo(request):
    if request.param == "file":
        return FileContentRepository(DATA)
    projects = FileContentRepository(DATA).list_projects()
    full = [FileContentRepository(DATA).project(p.slug) for p in projects]
    return InMemoryContentRepository(full)


def test_list_all(repo):
    slugs = {p.slug for p in repo.list_projects()}
    assert "this-website" in slugs


def test_featured_filter(repo):
    featured = repo.list_projects(featured=True)
    assert all(p.featured for p in featured)
    assert any(p.slug == "this-website" for p in featured)


def test_get_project_renders_body(repo):
    p = repo.project("this-website")
    assert isinstance(p, Project)
    assert "<" in p.body_html  # markdown rendered to HTML


def test_missing_raises(repo):
    with pytest.raises(NotFound):
        repo.project("does-not-exist")


def test_malformed_file_is_skipped(tmp_path):
    (tmp_path / "good.md").write_text(
        "---\nslug: good\ntitle: Good Project\n---\nA valid body.\n"
    )
    # tech must be a list; a string triggers a pydantic ValidationError on construct.
    (tmp_path / "bad.md").write_text(
        "---\nslug: bad\ntitle: Bad Project\ntech: not-a-list\n---\nOops.\n"
    )
    repo = FileContentRepository(tmp_path)
    projects = repo.list_projects()
    assert {p.slug for p in projects} == {"good"}


def test_missing_optional_fields_default(tmp_path):
    (tmp_path / "minimal.md").write_text(
        "---\nslug: minimal\ntitle: Minimal Project\n---\nJust a body.\n"
    )
    repo = FileContentRepository(tmp_path)
    p = repo.project("minimal")
    assert isinstance(p, Project)
    assert p.tech == []
    assert p.featured is False
    assert p.year is None
    assert p.highlights == []
    assert p.links == {}
