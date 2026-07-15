import logging
from pathlib import Path
from typing import Protocol

import frontmatter
import markdown

from rpc.content_rpc.contracts import Project, ProjectSummary
from rpc.exceptions import NotFound

logger = logging.getLogger(__name__)


class ContentRepository(Protocol):
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    def project(self, slug: str) -> Project: ...


def _summaries(projects):
    return [ProjectSummary.model_validate(p.model_dump()) for p in projects]


def _filter(projects, featured):
    if featured is None:
        return list(projects)
    return [p for p in projects if p.featured == featured]


class FileContentRepository:
    def __init__(self, data_dir):
        self._dir = Path(data_dir)

    def _load(self):
        out = {}
        for path in sorted(self._dir.glob("*.md")):
            try:
                post = frontmatter.load(path)
                meta = post.metadata
                slug = meta.get("slug", path.stem)
                out[slug] = Project(
                    slug=slug,
                    title=meta.get("title", ""),
                    blurb=meta.get("blurb", ""),
                    tech=meta.get("tech", []),
                    year=meta.get("year"),
                    featured=bool(meta.get("featured", False)),
                    role=meta.get("role", ""),
                    highlights=meta.get("highlights", []),
                    links=meta.get("links", {}),
                    body_html=markdown.markdown(post.content),
                )
            except Exception as exc:
                logger.warning("skipping unreadable project file %s: %s", path, exc)
                continue
        return out

    def list_projects(self, featured=None):
        return _summaries(_filter(self._load().values(), featured))

    def project(self, slug):
        projects = self._load()
        if slug not in projects:
            raise NotFound(f"no project: {slug}")
        return projects[slug]


class InMemoryContentRepository:
    def __init__(self, projects: list[Project]):
        self._projects = {p.slug: p for p in projects}

    def list_projects(self, featured=None):
        return _summaries(_filter(self._projects.values(), featured))

    def project(self, slug):
        if slug not in self._projects:
            raise NotFound(f"no project: {slug}")
        return self._projects[slug]
