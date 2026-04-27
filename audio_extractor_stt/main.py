from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
import uuid
from typing import AsyncGenerator

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

load_dotenv()

app = FastAPI(title="Minute Second API")

# Vite dev server 프록시를 위한 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# job_id → {status, queue, logs, result, error}
_jobs: dict[str, dict] = {}


# ─── POST /api/jobs — 파일 업로드 + 처리 시작 ────────────────────────────────

@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    meeting_type: str = Form("general"),
    ref_text: str = Form(""),
):
    suffix = os.path.splitext(file.filename or ".mp4")[1] or ".mp4"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    # 1 MB 청크 단위 streaming write — 2 GB 파일도 메모리에 통째로 올리지 않음
    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                await f.write(chunk)
    except Exception as exc:
        os.remove(tmp_path)
        raise HTTPException(500, f"파일 저장 실패: {exc}")

    job_id = str(uuid.uuid4())
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    _jobs[job_id] = {
        "status": "processing",
        "queue": queue,
        "logs": [],       # 재연결 시에도 이전 로그를 전송할 수 있도록 보관
        "result": None,
        "error": None,
    }

    asyncio.create_task(_process_job(job_id, tmp_path, queue, meeting_type, ref_text))
    return {"job_id": job_id}


# ─── SSE 처리 루프 ────────────────────────────────────────────────────────────

async def _process_job(job_id: str, video_path: str, queue: asyncio.Queue, meeting_type: str = "general", ref_text: str = "") -> None:
    from audio_extractor import async_extract_audio_from_video
    from stt_processor import process_audio
    from summarizer import summarize_text

    loop = asyncio.get_running_loop()

    def push(msg: str) -> None:
        """STT 스레드에서 안전하게 asyncio 큐에 메시지 전송."""
        _jobs[job_id]["logs"].append(msg)
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    def push_progress(overall: int, stage_label: str, stage_pct: int, eta_s: int | None = None) -> None:
        push(
            "__PROGRESS__:"
            + json.dumps(
                {"overall": overall, "stage_label": stage_label,
                 "stage_pct": stage_pct, "elapsed_s": int(time.monotonic() - _job_start),
                 "eta_s": eta_s},
                ensure_ascii=False,
            )
        )

    _job_start = time.monotonic()
    try:
        push_progress(1, "오디오 추출 중", 10)
        push("오디오 추출 중...")
        push_progress(5, "오디오 추출 완료", 100)
        async with async_extract_audio_from_video(video_path) as audio_path:
            # CPU-bound STT 처리 — asyncio.to_thread 로 이벤트 루프 블로킹 방지
            combined_text, speaker_text = await asyncio.to_thread(
                process_audio, audio_path, push
            )

        push_progress(95, "AI 요약 생성 중", 10)
        push("요약 생성 중...")
        summary = await asyncio.to_thread(summarize_text, combined_text, meeting_type, ref_text)
        push_progress(100, "완료", 100, 0)

        _jobs[job_id].update(
            status="done",
            result=dict(
                summary=summary,
                speaker_text=speaker_text,
                combined_text=combined_text,
            ),
        )
        push("__DONE__")

    except Exception as exc:
        _jobs[job_id].update(status="error", error=str(exc))
        push(f"__ERROR__:{exc}")

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        await queue.put(None)  # sentinel — SSE 스트림 종료


# ─── GET /api/jobs/{id}/events — SSE 진행 상태 스트림 ─────────────────────────

@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")

    job = _jobs[job_id]

    async def _generate() -> AsyncGenerator[dict, None]:
        # 재연결 시 이미 수집된 로그 먼저 전송
        for msg in list(job["logs"]):
            yield {"data": msg}

        # 이미 완료/실패 상태면 즉시 종료 이벤트 전송
        if job["status"] == "done":
            yield {"data": "__DONE__"}
            return
        if job["status"] == "error":
            yield {"data": f"__ERROR__:{job['error']}"}
            return

        # 진행 중이면 큐에서 실시간으로 읽어 전송
        queue: asyncio.Queue = job["queue"]
        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield {"data": msg}

    return EventSourceResponse(_generate())


# ─── GET /api/jobs/{id}/result — 최종 결과 ────────────────────────────────────

@app.get("/api/jobs/{job_id}/result")
async def job_result(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")
    job = _jobs[job_id]
    if job["status"] == "processing":
        raise HTTPException(202, "Still processing")
    if job["status"] == "error":
        raise HTTPException(500, job["error"])
    return job["result"]


# ─── 프로덕션 빌드 서빙 ────────────────────────────────────────────────────────
# `npm run build` 후 FastAPI 단독으로 서빙할 때 사용.
# 개발 중에는 Vite dev server(포트 5173)를 별도 실행.

_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_dist):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_dist, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _serve_spa(full_path: str):
        return FileResponse(os.path.join(_dist, "index.html"))
