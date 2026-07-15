"""The data-access layer for the content service — where projects come from.

This module is the clearest example of **dependency inversion** in the codebase.
Instead of the RPC tools (in ``tools.py``) reaching for files directly, they
depend on an *abstraction* — the ``ContentRepository`` Protocol — and a concrete
data source is *injected* from the outside (see ``deps.py``). That single idea
is what lets the exact same tool code run against real Markdown files in
production and against a hand-built list of objects in a unit test, with no
network and no filesystem.

Two implementations satisfy the Protocol:

  * ``FileContentRepository``    — production: reads ``*.md`` files (YAML
    frontmatter + Markdown body) out of a directory, with *per-file error
    isolation* so one malformed file can't take down the whole endpoint.
  * ``InMemoryContentRepository`` — tests: wraps an in-memory list of ``Project``
    objects, giving deterministic data with zero I/O.

Both return the SAME Pydantic contract types (``Project`` / ``ProjectSummary``)
that live in ``rpc/content_rpc`` and are shared, byte-for-byte, with every
caller across the RPC boundary. Those contracts are the single source of truth:
this service produces them, the web BFF and ai service consume them.
"""

import logging
from pathlib import Path
from typing import Protocol

# `frontmatter` splits a Markdown file into (YAML metadata, Markdown body);
# `markdown` renders that body to HTML. Content is authored as plain files on
# disk — no database — which keeps this learning project easy to edit in an editor.
import frontmatter
import markdown

# The wire contracts. Importing them HERE (in the service that owns the data) and
# ALSO in the callers guarantees producer and consumer agree on shape/validation.
from rpc.content_rpc.contracts import Project, ProjectSummary
# Part of the shared RPC exception hierarchy. Raising NotFound here is how this
# layer signals "no such project"; the RPC error handler in the shared library
# later maps that exception to an HTTP 404 for the caller (see main.py).
from rpc.exceptions import NotFound

logger = logging.getLogger(__name__)


class ContentRepository(Protocol):
    """Structural interface (a "port") describing any source of project data.

    This is a ``typing.Protocol``, i.e. a *structural* type: a class satisfies it
    simply by having methods with matching names/signatures — it does NOT have to
    subclass ``ContentRepository`` or import it. Both concrete repositories below
    conform without declaring any inheritance, which keeps the abstraction and
    the implementations decoupled.

    Why bother with an interface at all? So that the code that USES a repository
    (the RPC tools) can be written against these two methods alone and never
    learns whether the data lives in files, memory, or a database. Swapping the
    implementation is then a one-line change in ``deps.py``.
    """

    # List (optionally filtered to featured) — returns lightweight SUMMARIES,
    # the shape used by index/listing pages.
    def list_projects(self, featured: bool | None = None) -> list[ProjectSummary]: ...
    # Fetch one project by slug — returns the FULL Project (including rendered
    # body HTML). Must raise rpc.exceptions.NotFound when the slug is unknown.
    def project(self, slug: str) -> Project: ...


def _summaries(projects):
    """Down-project full ``Project`` records into ``ProjectSummary`` records.

    ``list_projects`` deliberately hands callers the *smaller* summary contract
    (no rendered ``body_html``, etc.) — listings don't need the full body, and
    keeping payloads lean is good RPC hygiene. We convert by dumping each Project
    to a dict and re-validating it as a ProjectSummary; Pydantic keeps the fields
    the summary declares and drops the rest, so the two contracts can't silently
    drift apart.
    """
    return [ProjectSummary.model_validate(p.model_dump()) for p in projects]


def _filter(projects, featured):
    """Apply the optional ``featured`` filter shared by both repositories.

    ``featured is None`` means "no filter — return everything" (note: this is
    distinct from ``featured=False``, which means "only the non-featured ones").
    Factored out here so the file-backed and in-memory repos filter identically.
    """
    if featured is None:
        return list(projects)
    return [p for p in projects if p.featured == featured]


class FileContentRepository:
    """Production repository: reads projects from Markdown-with-frontmatter files.

    Each ``*.md`` file in ``data_dir`` becomes one ``Project``. The file's YAML
    frontmatter supplies the structured fields (title, tech, year, ...) and the
    Markdown body becomes the rendered ``body_html``. Structurally implements the
    ``ContentRepository`` Protocol (no explicit inheritance needed).
    """

    def __init__(self, data_dir):
        # Store the directory to scan. Coerced to Path so callers may pass a str
        # (e.g. from an env var) and we still get Path conveniences like .glob().
        self._dir = Path(data_dir)

    def _load(self):
        """Scan the directory and parse every file into a ``{slug: Project}`` map.

        Design notes worth internalizing:

        * **Read-on-demand, no caching here.** Every call re-reads the directory,
          so edits to the Markdown show up without restarting the service. (The
          service-level caching decision lives in ``deps.py`` via ``lru_cache``.)
        * **Per-file error isolation.** A single unparseable/broken file must not
          break ``list_projects``/``project`` for all the *other* files, so each
          file is parsed inside its own ``try`` and a failure is logged-and-
          skipped rather than propagated. This is a small dose of graceful
          degradation right at the data source.
        """
        out = {}
        # `sorted(...)` gives a stable, deterministic ordering across runs and
        # platforms — otherwise glob order (and thus listing order) is arbitrary.
        for path in sorted(self._dir.glob("*.md")):
            try:
                # Parse the file into metadata (frontmatter) + content (body).
                post = frontmatter.load(path)
                meta = post.metadata
                # Slug identifies the project in URLs and RPC calls. Prefer an
                # explicit `slug:` in frontmatter; otherwise fall back to the
                # filename without extension (e.g. `foo.md` -> "foo").
                slug = meta.get("slug", path.stem)
                # Build the shared Project contract. Every `.get(..., default)`
                # keeps a file with missing optional fields still loadable, while
                # Pydantic validates types as the object is constructed. Using
                # the contract type here (not a bare dict) is what lets this value
                # cross the RPC boundary unchanged.
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
                    # Render the Markdown body to HTML once, at load time, so
                    # callers receive display-ready content over the wire.
                    body_html=markdown.markdown(post.content),
                )
            except Exception as exc:
                # Per-file isolation: log the bad file and keep going so the rest
                # of the catalog still serves. Broad `except` is intentional here
                # — any parse/validation error for one file is non-fatal.
                logger.warning("skipping unreadable project file %s: %s", path, exc)
                continue
        return out

    def list_projects(self, featured=None):
        # Load everything, apply the shared featured-filter, then narrow to
        # summaries. Same two helpers the in-memory repo uses, so behavior matches.
        return _summaries(_filter(self._load().values(), featured))

    def project(self, slug):
        projects = self._load()
        # Unknown slug -> NotFound. The shared RPC error handler turns this into
        # a 404 for the caller (rather than a 500), so a bad URL is handled
        # cleanly end-to-end across the service boundary.
        if slug not in projects:
            raise NotFound(f"no project: {slug}")
        return projects[slug]


class InMemoryContentRepository:
    """Test double: serves a fixed list of ``Project`` objects from memory.

    This is the "fake" that makes the dependency-inversion design pay off. Unit
    tests (and the in-process e2e bridge) inject this instead of the file-backed
    repo, so tools/endpoints can be exercised with deterministic data and *zero*
    filesystem or network I/O. It implements the same Protocol, so the code under
    test can't tell the difference.
    """

    def __init__(self, projects: list[Project]):
        # Index the provided projects by slug for O(1) lookup, mirroring the
        # `{slug: Project}` shape that FileContentRepository._load() produces.
        self._projects = {p.slug: p for p in projects}

    def list_projects(self, featured=None):
        # Identical pipeline to the file repo — the only difference is the source
        # of the Projects (in-memory dict vs. parsed files).
        return _summaries(_filter(self._projects.values(), featured))

    def project(self, slug):
        # Same NotFound contract as the file repo, so tests observe the same
        # 404-mapping behavior the real service exhibits.
        if slug not in self._projects:
            raise NotFound(f"no project: {slug}")
        return self._projects[slug]
