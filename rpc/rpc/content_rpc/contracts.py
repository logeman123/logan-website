"""Pydantic data contracts for the **content** service's RPC surface.

These classes are the *wire schema* for content. They define exactly what a
``list_projects``/``get_project`` request accepts and what its response looks like. Both the
content server (which produces these objects) and every caller (which parses them back) import
THIS module, so the two ends can never disagree about the shape of the data -- the model IS the
contract.

Two response shapes on purpose: ``ProjectSummary`` vs ``Project``
----------------------------------------------------------------
This is the key design idea to notice. We deliberately publish two overlapping models:

* ``ProjectSummary`` -- the *lightweight* view used for LISTS (the /work index, chat grounding,
  etc). It carries just enough to render a card or a menu entry: identity, title, a short blurb,
  the tech stack, the year, and whether it's featured. No heavy HTML body.

* ``Project`` -- the *full* view used for a single DETAIL page. It ``extends`` ``ProjectSummary``
  (via subclassing) and adds the expensive/verbose fields: ``role``, ``highlights``, external
  ``links``, and the rendered ``body_html``.

Why split them? A listing endpoint may return many projects; shipping every project's full
rendered HTML body in that list would be wasteful and slow. So ``list_projects`` returns the
slim summaries and ``get_project`` returns the full record. Because ``Project`` *inherits* from
``ProjectSummary``, the summary fields are defined in exactly one place and stay in sync -- a
detail response is always a valid superset of a summary response.

Note that request ("...In") and response models are separate types. The ``*In`` models validate
inbound arguments; ``ProjectSummary``/``Project`` validate outbound data. Keeping them distinct
means the input surface can evolve independently of the output surface.
"""

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    """Lightweight projection of a project -- what list/index views need, nothing more.

    Returned (as a ``list``) by the ``list_projects`` RPC tool. Every field except ``slug`` and
    ``title`` has a default so the content service can build a summary even from a sparse
    Markdown frontmatter block without raising validation errors.
    """

    slug: str  # URL-safe stable identifier; the primary key used by get_project(slug=...).
    title: str  # Human-readable project name shown as the card/heading text.
    blurb: str = ""  # One-line teaser for list cards; empty string is a valid "no blurb yet".
    tech: list[str] = []  # Tech-stack tags (e.g. ["FastAPI", "HTMX"]); defaults to empty list.
    year: int | None = None  # Optional year; None means "unspecified", distinct from 0.
    featured: bool = False  # Drives the ?featured filter on list_projects and highlight styling.


class Project(ProjectSummary):
    """Full project record -- the detail view, a strict superset of ``ProjectSummary``.

    Returned by the ``get_project`` RPC tool. By subclassing ``ProjectSummary`` we reuse every
    summary field verbatim (single source of truth) and only declare the extra, heavier fields
    that a single-project page needs. Any ``Project`` therefore also validates as a summary.
    """

    role: str = ""  # The author's role on the project (e.g. "Lead engineer").
    highlights: list[str] = []  # Bullet-point accomplishments rendered on the detail page.
    links: dict[str, str] = {}  # Label -> URL map (e.g. {"repo": "https://...", "demo": ...}).
    body_html: str = ""  # Pre-rendered Markdown body as HTML; the "heavy" field kept out of lists.


class ListProjectsIn(BaseModel):
    """Typed arguments for the ``list_projects`` RPC tool.

    Wrapping even a single optional argument in a model keeps the RPC dispatch uniform: every
    tool takes one validated request object, and adding a new filter later is a backward-
    compatible field addition rather than a signature change.
    """

    featured: bool | None = None  # Tri-state filter: None=all, True=only featured, False=only not.


class GetProjectIn(BaseModel):
    """Typed arguments for the ``get_project`` RPC tool -- just the project ``slug`` to fetch."""

    slug: str  # Required; matched against ProjectSummary.slug to select one project.
