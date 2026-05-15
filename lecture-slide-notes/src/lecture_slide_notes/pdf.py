from __future__ import annotations

import re
import textwrap
from pathlib import Path

from .models import SlideRecord


def find_korean_font() -> tuple[str | None, str | None, int | None]:
    candidates = [
        ("MalgunGothic", r"C:\Windows\Fonts\malgun.ttf", None),
        ("MalgunGothicBold", r"C:\Windows\Fonts\malgunbd.ttf", None),
        ("NotoSansCJK", r"C:\Windows\Fonts\NotoSansCJKkr-Regular.otf", None),
        ("NanumGothic", r"C:\Windows\Fonts\NanumGothic.ttf", None),
        ("AppleGothic", "/System/Library/Fonts/AppleGothic.ttf", None),
        ("NotoSansCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ]
    for name, path, index in candidates:
        if Path(path).exists():
            return name, path, index
    return None, None, None


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[`*_>#|\[\](){}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def wrap_lines(text: str, width: int, height: int, font_size: int) -> list[str]:
    chars_per_line = max(40, int((width - 48) / (font_size * 0.55)))
    max_lines = max(12, int((height - 48) / (font_size * 1.25)))
    lines: list[str] = []
    for paragraph in re.split(r"\s*---\s*|\n+", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines.extend(textwrap.wrap(paragraph, width=chars_per_line))
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def draw_searchable_text(pdf, text: str, width: int, height: int, font_name: str, invisible: bool) -> None:
    if not text:
        return
    font_size = max(9, min(14, int(width / 140)))
    leading = font_size * 1.25
    pdf.saveState()
    pdf.setFont(font_name, font_size)
    pdf.setFillColorRGB(0, 0, 0)
    text_object = pdf.beginText(24, height - 28)
    text_object.setLeading(leading)
    if invisible:
        text_object.setTextRenderMode(3)
    for line in wrap_lines(text, width, height, font_size):
        try:
            text_object.textLine(line)
        except Exception:
            continue
    pdf.drawText(text_object)
    pdf.restoreState()


def write_searchable_pdf(
    slides: list[SlideRecord],
    output_pdf: Path,
    *,
    add_text_layer: bool = True,
    ocr_layer_mode: str = "hidden",
) -> None:
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas as rl_canvas

    font_name = None
    if add_text_layer:
        font_name, font_path, font_index = find_korean_font()
        if font_name and font_path:
            if font_path.lower().endswith(".ttc") and font_index is not None:
                pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=font_index))
            else:
                pdfmetrics.registerFont(TTFont(font_name, font_path))

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf = rl_canvas.Canvas(str(output_pdf))
    for slide in slides:
        image_path = slide.pdf_file or slide.file
        with Image.open(image_path) as image:
            width, height = image.size
        pdf.setPageSize((width, height))
        if add_text_layer and font_name:
            text = strip_markdown(slide.corrected_text or slide.ocr_text)
            draw_searchable_text(pdf, text, width, height, font_name, invisible=ocr_layer_mode == "invisible")
        pdf.drawImage(ImageReader(str(image_path)), 0, 0, width, height)
        pdf.showPage()
    pdf.save()
