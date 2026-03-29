from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies import get_pipeline
from app.services.pipeline_service import PipelineResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

_ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_results_store: dict[str, PipelineResult] = {}
_progress_queues: dict[str, asyncio.Queue] = {}


async def _run_pipeline(
    analysis_id: str,
    file_bytes: bytes,
    mime_type: str,
) -> None:
    queue = _progress_queues[analysis_id]

    async def on_progress(step: int, total: int, name: str, status: str) -> None:
        logger.info(
            "[%s] Step %d/%d %-30s %s",
            analysis_id, step, total, name, status.upper(),
        )
        await queue.put({
            "event": "step_update",
            "step": step,
            "total": total,
            "name": name,
            "status": status,
        })

    pipeline = get_pipeline()
    logger.info("[%s] Pipeline started (mime=%s, size=%d bytes)", analysis_id, mime_type, len(file_bytes))
    try:
        result = await pipeline.run(file_bytes, mime_type, on_progress=on_progress)
        _results_store[analysis_id] = result
        logger.info("[%s] Pipeline finished successfully", analysis_id)
        await queue.put({"event": "complete", "analysis_id": analysis_id})
    except Exception:
        logger.exception("[%s] Pipeline FAILED", analysis_id)
        await queue.put({"event": "error", "detail": "Analysis failed. Please try again."})


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)) -> dict:
    if file.content_type not in _ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Upload a PDF or DOCX.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    analysis_id = uuid.uuid4().hex[:12]
    _progress_queues[analysis_id] = asyncio.Queue()

    logger.info(
        "[%s] Upload received: %s (%s, %d bytes)",
        analysis_id, file.filename, file.content_type, len(file_bytes),
    )
    asyncio.create_task(_run_pipeline(analysis_id, file_bytes, file.content_type))

    return {"analysis_id": analysis_id}


@router.get("/progress/{analysis_id}")
async def progress_stream(analysis_id: str) -> StreamingResponse:
    queue = _progress_queues.get(analysis_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    logger.debug("[%s] SSE client connected", analysis_id)

    async def event_generator():
        while True:
            msg = await queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("event") in ("complete", "error"):
                break
        _progress_queues.pop(analysis_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def get_result(analysis_id: str) -> PipelineResult | None:
    return _results_store.get(analysis_id)
