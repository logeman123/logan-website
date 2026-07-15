from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import chat, home, resume, work

BASE = Path(__file__).parent
app = FastAPI(title="web")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(home.router)
app.include_router(work.router)
app.include_router(chat.router)
app.include_router(resume.router)


@app.get("/health")
def health():
    return {"status": "ok"}
