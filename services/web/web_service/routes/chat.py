from fastapi import APIRouter, Depends, Form, Request

from rpc.ai_rpc.client import AiSource
from rpc.exceptions import RPCError

from ..deps import get_ai
from ..templating import templates

router = APIRouter()


@router.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@router.post("/chat")
def chat_send(request: Request, message: str = Form(...), ai: AiSource = Depends(get_ai)):
    try:
        reply = ai.chat(message=message).reply
    except RPCError:
        reply = "The chat is temporarily unavailable — please try again shortly."
    return templates.TemplateResponse(request, "_chat_reply.html", {"message": message, "reply": reply})
