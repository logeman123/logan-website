from fastapi import FastAPI

from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_chat, get_settings
from .rpc_tools import build_ai_registry

app = FastAPI(title="ai")
add_rpc_error_handler(app)
app.include_router(create_rpc_router(build_ai_registry(get_chat()), get_settings().service_token))


@app.get("/health")
def health():
    return {"status": "ok"}
