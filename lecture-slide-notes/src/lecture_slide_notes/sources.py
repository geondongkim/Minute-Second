from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .models import LectureSource


VIMEO_ID_RE = re.compile(r"(?:player\.vimeo\.com/video/|vimeo\.com/(?:video/)?)(\d+)")
YOUTUBE_FALLBACK_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?[^\s#]*v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)
IFRAME_RE = re.compile(r"<iframe[^>]+src=[\"']([^\"']*player\.vimeo\.com/video/[^\"']+)[\"']", re.IGNORECASE)
YOUTUBE_IFRAME_RE = re.compile(
    r"<iframe[^>]+src=[\"']([^\"']*(?:youtube\.com/embed/|youtube-nocookie\.com/embed/)[^\"']+)[\"']",
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
MANIFEST_RE = re.compile(r"https?://[^\s'\"<>]+(?:\.m3u8|\.mpd|playlist\.json)[^\s'\"<>]*", re.IGNORECASE)


def parse_vimeo_id(value: str) -> str | None:
    match = VIMEO_ID_RE.search(value)
    return match.group(1) if match else None


def build_vimeo_player_url(video_id: str) -> str:
    return f"https://player.vimeo.com/video/{video_id}"


def parse_youtube_id(value: str) -> str | None:
    parsed = urlparse(value)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    if host in {"youtube.com", "music.youtube.com", "youtube-nocookie.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                return video_id
        for prefix in ("/embed/", "/shorts/", "/live/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path.removeprefix(prefix).split("/", 1)[0]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                    return candidate
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/", 1)[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate
    match = YOUTUBE_FALLBACK_RE.search(value)
    return match.group(1) if match else None


def build_youtube_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def is_manifest_url(value: str) -> bool:
    lowered = value.lower()
    return ".m3u8" in lowered or ".mpd" in lowered or "playlist.json" in lowered


def looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_vimeo_iframe(html: str) -> str | None:
    match = IFRAME_RE.search(html)
    return match.group(1).replace("&amp;", "&") if match else None


def extract_youtube_iframe(html: str) -> str | None:
    match = YOUTUBE_IFRAME_RE.search(html)
    return match.group(1).replace("&amp;", "&") if match else None


def extract_page_title(html: str) -> str | None:
    match = TITLE_RE.search(html)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title or None


def extract_manifest_candidates(text: str) -> list[str]:
    return sorted({candidate.replace("&amp;", "&") for candidate in MANIFEST_RE.findall(text)})


def fetch_text(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get("content-type", "")
    encoding = "utf-8"
    match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
    if match:
        encoding = match.group(1).strip()
    return data.decode(encoding, errors="replace")


def load_capture_file(path: Path) -> LectureSource:
    data = json.loads(path.read_text(encoding="utf-8"))
    player_url = data.get("playerUrl") or data.get("player_url")
    youtube_url = data.get("youtubeUrl") or data.get("youtube_url")
    manifest_url = data.get("manifestUrl") or data.get("manifest_url") or data.get("hlsUrl")
    referer = data.get("referer") or data.get("pageUrl") or data.get("page_url")
    original = player_url or youtube_url or manifest_url or data.get("url") or data.get("webpage_url") or referer or str(path)
    vimeo_id = parse_vimeo_id(original) if original else None
    youtube_id = parse_youtube_id(original) if original else None
    source_type = "unknown"
    if player_url or vimeo_id:
        source_type = "vimeo"
    elif youtube_url or youtube_id:
        source_type = "youtube"
    elif manifest_url:
        source_type = "manifest"
    return LectureSource(
        source_type=source_type,
        original=original,
        player_url=player_url
        or youtube_url
        or (build_vimeo_player_url(vimeo_id) if vimeo_id else None)
        or (build_youtube_watch_url(youtube_id) if youtube_id else None),
        referer=referer,
        manifest_url=manifest_url,
        video_id=vimeo_id or youtube_id,
        title=data.get("title"),
        metadata=data,
    )


class SourceResolver:
    def resolve(
        self,
        value: str,
        *,
        referer: str | None = None,
        title: str | None = None,
        fetch_page: bool = False,
    ) -> LectureSource:
        path = Path(value)
        if path.exists():
            if path.suffix.lower() == ".json":
                return load_capture_file(path)
            return LectureSource(source_type="file", original=value, local_file=path.resolve(), title=title or path.stem)

        if is_manifest_url(value):
            return LectureSource(
                source_type="manifest",
                original=value,
                manifest_url=value,
                referer=referer,
                video_id=parse_vimeo_id(value),
                title=title,
            )

        video_id = parse_vimeo_id(value)
        if video_id:
            return LectureSource(
                source_type="vimeo",
                original=value,
                player_url=build_vimeo_player_url(video_id),
                referer=referer,
                video_id=video_id,
                title=title,
            )

        youtube_id = parse_youtube_id(value)
        if youtube_id:
            return LectureSource(
                source_type="youtube",
                original=value,
                player_url=build_youtube_watch_url(youtube_id),
                referer=referer,
                video_id=youtube_id,
                title=title,
            )

        if looks_like_url(value):
            source = LectureSource(source_type="course_page", original=value, referer=referer or value, title=title)
            if fetch_page:
                html = fetch_text(value)
                player_url = extract_vimeo_iframe(html)
                if player_url:
                    source.player_url = player_url
                    source.video_id = parse_vimeo_id(player_url)
                    source.source_type = "vimeo"
                else:
                    youtube_url = extract_youtube_iframe(html)
                    if youtube_url:
                        source.player_url = youtube_url
                        source.video_id = parse_youtube_id(youtube_url)
                        source.source_type = "youtube"
                source.title = title or extract_page_title(html)
                source.metadata["manifest_candidates"] = extract_manifest_candidates(html)
            return source

        return LectureSource(source_type="unknown", original=value, referer=referer, title=title)
