from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from app.core.configs.settings import settings

from app.core.pipeline.attendance_pipline import AttendancePipeline

router = APIRouter(prefix="/attendance", tags=["attendance"])


def get_attendance_worker(request: Request) -> AttendancePipeline:
    return request.app.state.attendance_worker


@router.get("/status")
async def attendance_status(request: Request) -> dict:
    worker = get_attendance_worker(request)
    return {
        **worker.status(),
        "latest_result": worker.get_latest_result(),
    }


@router.post("/start")
async def start_attendance(request: Request) -> dict:
    worker = get_attendance_worker(request)
    started = worker.start()
    return {
        "started": started,
        **worker.status(),
    }


@router.post("/stop")
async def stop_attendance(request: Request) -> dict:
    worker = get_attendance_worker(request)
    was_running = worker.is_running
    await worker.stop()
    return {
        "stopped": was_running,
        **worker.status(),
    }


@router.get("/stream")
async def attendance_stream(
    request: Request,
    fps: float = Query(default=settings.attendance_stream_fps, ge=1.0, le=30.0),
) -> StreamingResponse:
    worker = get_attendance_worker(request)
    frame_delay = 1.0 / max(float(fps), 1.0)

    async def frame_generator():
        while True:
            jpeg = worker.get_annotated_frame_jpeg()
            if jpeg is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg
                    + b"\r\n"
                )
            await asyncio.sleep(frame_delay)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
