from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes.analysis import router as analysis_router
from app.api.routes.upload import router as upload_router
from app.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-40s │ %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("grpc").setLevel(logging.WARNING)
logging.getLogger("python_multipart").setLevel(logging.WARNING)

app = FastAPI(title=settings.app_title)

_BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")
templates = Jinja2Templates(directory=_BASE / "templates")

app.include_router(upload_router)
app.include_router(analysis_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/progress/{analysis_id}", response_class=HTMLResponse)
async def progress_page(request: Request, analysis_id: str):
    return templates.TemplateResponse(
        request, "progress.html", {"analysis_id": analysis_id}
    )


@app.get("/result/{analysis_id}", response_class=HTMLResponse)
async def result_page(request: Request, analysis_id: str):
    return templates.TemplateResponse(
        request, "result.html", {"analysis_id": analysis_id}
    )
