from fastapi import APIRouter, Request

from ..templating import templates

router = APIRouter()


@router.get("/resume")
def resume(request: Request):
    return templates.TemplateResponse(request, "resume.html", {})
