from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OcrResult:
    text: str
    engine: str
    language: str
    available: bool
    error: str | None = None


class TesseractOcr:
    def __init__(self, language: str = "kor+eng") -> None:
        self.language = language

    def is_available(self) -> bool:
        if not shutil.which("tesseract"):
            return False
        try:
            import pytesseract  # noqa: F401
        except Exception:
            return False
        return True

    def extract(self, image_path: Path) -> OcrResult:
        if not self.is_available():
            return OcrResult(text="", engine="tesseract", language=self.language, available=False)
        try:
            from PIL import Image
            import pytesseract

            with Image.open(image_path) as image:
                text = pytesseract.image_to_string(image, lang=self.language)
            return OcrResult(text=text.strip(), engine="tesseract", language=self.language, available=True)
        except Exception as exc:
            return OcrResult(text="", engine="tesseract", language=self.language, available=True, error=str(exc))


def write_ocr_texts(slides, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for slide in slides:
        (output_dir / f"slide_{slide.slide:03d}.txt").write_text(slide.ocr_text, encoding="utf-8")
