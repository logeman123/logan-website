from pydantic import BaseModel


class ProjectSummary(BaseModel):
    slug: str
    title: str
    blurb: str = ""
    tech: list[str] = []
    year: int | None = None
    featured: bool = False


class Project(ProjectSummary):
    role: str = ""
    highlights: list[str] = []
    links: dict[str, str] = {}
    body_html: str = ""


class ListProjectsIn(BaseModel):
    featured: bool | None = None


class GetProjectIn(BaseModel):
    slug: str
