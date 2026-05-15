from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


SourceType = Literal["file", "vimeo", "youtube", "manifest", "course_page", "unknown"]


@dataclass(slots=True)
class LectureSource:
    source_type: SourceType
    original: str
    player_url: str | None = None
    referer: str | None = None
    manifest_url: str | None = None
    local_file: Path | None = None
    video_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def download_url(self) -> str:
        return self.player_url or self.manifest_url or self.original


@dataclass(slots=True)
class SlideRecord:
    slide: int
    timestamp: float
    timestamp_text: str
    file: Path
    source_frame: str | None = None
    pdf_file: Path | None = None
    ocr_text: str = ""
    corrected_text: str = ""

    def to_manifest(self, base_dir: Path | None = None) -> dict[str, Any]:
        def path_value(path: Path | None) -> str | None:
            if not path:
                return None
            if base_dir:
                try:
                    return path.relative_to(base_dir).as_posix()
                except ValueError:
                    return str(path)
            return str(path)

        return {
            "slide": self.slide,
            "timestamp": self.timestamp,
            "timestampText": self.timestamp_text,
            "file": path_value(self.file),
            "pdfFile": path_value(self.pdf_file),
            "sourceFrame": self.source_frame,
            "ocrTextLength": len(self.ocr_text),
            "correctedTextLength": len(self.corrected_text),
        }


@dataclass(slots=True)
class SlideDetectionOptions:
    sample_rate: float = 2.0
    min_gap: float = 8.0
    threshold: int = 22
    width: int = 1280
    pdf_width: int = 0
    stable_seconds: float = 2.0
    stability_threshold: int = 10
    dedupe_threshold: int = 18
    max_slides: int = 0
    keep_frames: bool = False
    create_contact_sheet: bool = True


@dataclass(slots=True)
class ProcessingOptions:
    detection: SlideDetectionOptions = field(default_factory=SlideDetectionOptions)
    export_pdf: bool = True
    add_ocr_layer: bool = True
    ocr_layer_mode: Literal["hidden", "invisible"] = "hidden"
    ocr_lang: str = "kor+eng"
    no_ocr: bool = False
    correct_with_gemini: bool = False
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None


@dataclass(slots=True)
class PipelineResult:
    title: str
    output_dir: Path
    slides: list[SlideRecord]
    markdown_path: Path
    manifest_path: Path
    pdf_path: Path | None = None
    contact_sheet_path: Path | None = None
    video_path: Path | None = None
