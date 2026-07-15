from fastapi import APIRouter, Depends, Request

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import NotFound, RPCError

from ..deps import get_content
from ..templating import templates

router = APIRouter()


@router.get("/work")
def work_list(request: Request, content: ContentSource = Depends(get_content)):
    try:
        projects = content.list_projects()
        error = None
    except RPCError:
        projects, error = [], "Work is temporarily unavailable."
    return templates.TemplateResponse(request, "work_list.html", {"projects": projects, "error": error})


@router.get("/work/{slug}")
def work_detail(slug: str, request: Request, content: ContentSource = Depends(get_content)):
    try:
        project = content.get_project(slug)
    except NotFound:
        return templates.TemplateResponse(
            request, "work_detail.html", {"project": None, "error": None}, status_code=404)
    except RPCError:
        return templates.TemplateResponse(
            request, "work_detail.html", {"project": None, "error": "Temporarily unavailable."})
    return templates.TemplateResponse(request, "work_detail.html", {"project": project, "error": None})
