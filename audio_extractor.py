import asyncio
import contextlib
import os
import tempfile

import ffmpeg


@contextlib.contextmanager
def extract_audio_from_video(video_path: str):
    """
    Extracts audio from a video file into a temporary WAV file (16kHz, mono).
    Yields the path to the temporary audio file, which is deleted upon exit.
    Synchronous — suitable for non-async contexts.
    """
    fd, audio_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, ac=1, ar="16k", format="wav", loglevel="error")
            .run(overwrite_output=True)
        )
        yield audio_path
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def _run_ffmpeg_sync(video_path: str, audio_path: str) -> None:
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, ac=1, ar="16k", format="wav", loglevel="error")
        .run(overwrite_output=True)
    )


@contextlib.asynccontextmanager
async def async_extract_audio_from_video(video_path: str):
    """
    Async version — runs ffmpeg in a thread pool to avoid blocking the event loop.
    Use inside FastAPI / asyncio contexts.
    """
    fd, audio_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        await asyncio.to_thread(_run_ffmpeg_sync, video_path, audio_path)
        yield audio_path
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
