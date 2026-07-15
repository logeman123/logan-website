from fastapi import APIRouter, Depends, Request

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import RPCError

from ..deps import get_content
from ..templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, content: ContentSource = Depends(get_content)):
    try:
        featured = content.list_projects(featured=True)
        error = None
    except RPCError:
        featured, error = [], "Featured work is temporarily unavailable."
    return templates.TemplateResponse(request, "index.html", {"featured": featured, "error": error})
