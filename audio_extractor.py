import tempfile
import ffmpeg
import os
import contextlib

@contextlib.contextmanager
def extract_audio_from_video(video_path: str):
    """
    Extracts audio from a video file into a temporary WAV file (16kHz, mono).
    Yields the path to the temporary audio file, which is deleted upon exit.
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
