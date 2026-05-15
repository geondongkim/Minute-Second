from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import LectureSource


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def safe_stem(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    value = re.sub(r"\s+", "_", value).strip("._ ")
    return value[:120] or "lecture"


def cookies_from_browser_tuple(value: str | None) -> tuple[str, str | None, str | None, str | None] | None:
    if not value:
        return None
    parts = value.split(":", 1)
    browser = parts[0]
    profile = parts[1] if len(parts) > 1 and parts[1] else None
    return (browser, profile, None, None)


def find_downloaded_file(output_dir: Path, stem: str) -> Path | None:
    matches = [path for path in output_dir.glob(f"{stem}.*") if path.suffix.lower() in VIDEO_EXTENSIONS]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


class DownloadManager:
    def __init__(self, *, ffmpeg_location: str | None = None, cookies_from_browser: str | None = None) -> None:
        self.ffmpeg_location = ffmpeg_location
        self.cookies_from_browser = cookies_from_browser

    def extract_info(self, source: LectureSource, *, download: bool = False) -> dict[str, Any]:
        from yt_dlp import YoutubeDL

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if source.referer:
            options["http_headers"] = {"Referer": source.referer}
        cookies = cookies_from_browser_tuple(self.cookies_from_browser)
        if cookies:
            options["cookiesfrombrowser"] = cookies

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(source.download_url, download=download)
            return ydl.sanitize_info(info)

    def download(
        self,
        source: LectureSource,
        output_dir: Path,
        *,
        filename_stem: str | None = None,
        format_selector: str = "bv*+ba/b",
    ) -> Path:
        from yt_dlp import YoutubeDL

        output_dir.mkdir(parents=True, exist_ok=True)
        stem = safe_stem(filename_stem or source.title or source.video_id or "lecture")
        output_template = str(output_dir / f"{stem}.%(ext)s")
        downloaded_paths: list[Path] = []

        def progress_hook(data: dict[str, Any]) -> None:
            if data.get("status") == "finished" and data.get("filename"):
                downloaded_paths.append(Path(data["filename"]))

        options: dict[str, Any] = {
            "format": format_selector,
            "outtmpl": output_template,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "progress_hooks": [progress_hook],
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
        }
        if self.ffmpeg_location:
            options["ffmpeg_location"] = self.ffmpeg_location
        if source.referer:
            options["http_headers"] = {"Referer": source.referer}
        cookies = cookies_from_browser_tuple(self.cookies_from_browser)
        if cookies:
            options["cookiesfrombrowser"] = cookies

        with YoutubeDL(options) as ydl:
            ydl.download([source.download_url])

        final_file = find_downloaded_file(output_dir, stem)
        if final_file:
            return final_file
        for path in reversed(downloaded_paths):
            if path.exists():
                return path
        raise FileNotFoundError(f"Downloaded video not found in {output_dir}")
