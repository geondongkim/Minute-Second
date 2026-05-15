from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import LectureSource, SlideRecord


def _relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


def build_notebooklm_markdown(
    *,
    title: str,
    source: LectureSource | None,
    slides: list[SlideRecord],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines: list[str] = [
        "---",
        f"title: {title}",
        f"generated_at: {generated_at}",
        f"slide_count: {len(slides)}",
    ]
    if source:
        lines.extend(
            [
                f"source_type: {source.source_type}",
                f"source: {source.original}",
            ]
        )
        if source.referer:
            lines.append(f"referer: {source.referer}")
        if source.video_id:
            lines.append(f"vimeo_id: {source.video_id}")
    lines.extend(["---", "", f"# {title}", "", "## Lecture Metadata", "", f"- Slide count: {len(slides)}"])
    if source and source.referer:
        lines.append(f"- Lesson page: {source.referer}")
    if source and source.player_url:
        lines.append(f"- Vimeo player: {source.player_url}")
    lines.extend(["", "## Slide Index", ""])

    for slide in slides:
        lines.append(f"- Slide {slide.slide:03d}: {slide.timestamp_text}")

    for slide in slides:
        image_path = slide.pdf_file or slide.file
        lines.extend(
            [
                "",
                "---",
                "",
                f"## Slide {slide.slide:03d} - {slide.timestamp_text}",
                "",
                f"![Slide {slide.slide:03d}]({_relative(image_path, output_path.parent)})",
                "",
            ]
        )
        if slide.corrected_text.strip():
            lines.extend([slide.corrected_text.strip(), ""])
        if slide.ocr_text.strip():
            lines.extend(["### OCR Source Text", "", slide.ocr_text.strip(), ""])
        if not slide.corrected_text.strip() and not slide.ocr_text.strip():
            lines.extend(["> No OCR text was extracted for this slide.", ""])

    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
