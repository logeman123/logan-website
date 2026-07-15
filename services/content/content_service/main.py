from fastapi import FastAPI

from rpc.server import add_rpc_error_handler, create_rpc_router

from .deps import get_repository, get_settings
from .tools import build_content_registry

app = FastAPI(title="content")
add_rpc_error_handler(app)
app.include_router(create_rpc_router(build_content_registry(get_repository()), get_settings().service_token))


@app.get("/health")
def health():
    return {"status": "ok"}
