from __future__ import annotations

import json
from pathlib import Path

from .downloader import DownloadManager, safe_stem
from .llm import GeminiCorrector
from .markdown import build_notebooklm_markdown
from .models import LectureSource, PipelineResult, ProcessingOptions
from .ocr import TesseractOcr, write_ocr_texts
from .pdf import write_searchable_pdf
from .serialization import to_jsonable
from .slides import create_contact_sheet, create_pdf_slide_images, extract_slides
from .sources import SourceResolver


def write_manifest(result: PipelineResult, source: LectureSource | None, options: ProcessingOptions) -> None:
    manifest = {
        "title": result.title,
        "video": str(result.video_path) if result.video_path else None,
        "outputDir": str(result.output_dir),
        "source": to_jsonable(source) if source else None,
        "options": {
            "detection": to_jsonable(options.detection),
            "exportPdf": options.export_pdf,
            "addOcrLayer": options.add_ocr_layer,
            "ocrLayerMode": options.ocr_layer_mode,
            "ocrLang": options.ocr_lang,
            "noOcr": options.no_ocr,
            "correctWithGemini": options.correct_with_gemini,
            "geminiModel": options.gemini_model,
        },
        "slides": [slide.to_manifest(result.output_dir) for slide in result.slides],
    }
    result.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def enrich_slides_with_ocr_and_llm(slides, output_dir: Path, title: str, options: ProcessingOptions) -> None:
    if not options.no_ocr:
        ocr = TesseractOcr(language=options.ocr_lang)
        for slide in slides:
            image_path = slide.pdf_file or slide.file
            result = ocr.extract(image_path)
            slide.ocr_text = result.text
            if result.error:
                slide.ocr_text = f"OCR error: {result.error}"
        write_ocr_texts(slides, output_dir / "ocr_text")

    if options.correct_with_gemini:
        corrector = GeminiCorrector(model=options.gemini_model, api_key=options.gemini_api_key)
        for slide in slides:
            slide.corrected_text = corrector.correct_slide_text(
                title=title,
                slide_number=slide.slide,
                timestamp=slide.timestamp_text,
                ocr_text=slide.ocr_text,
            )


def process_video(
    video_path: Path,
    output_dir: Path,
    *,
    options: ProcessingOptions | None = None,
    source: LectureSource | None = None,
    title: str | None = None,
) -> PipelineResult:
    options = options or ProcessingOptions()
    video_path = video_path.resolve()
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    lecture_title = title or (source.title if source and source.title else video_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)
    slides = extract_slides(video_path, output_dir, options.detection)

    if options.export_pdf:
        create_pdf_slide_images(video_path, slides, output_dir / "slides_pdf", width=options.detection.pdf_width)

    enrich_slides_with_ocr_and_llm(slides, output_dir, lecture_title, options)

    markdown_path = output_dir / f"{safe_stem(lecture_title)}_notes.md"
    build_notebooklm_markdown(title=lecture_title, source=source, slides=slides, output_path=markdown_path)

    contact_sheet_path = None
    if options.detection.create_contact_sheet:
        contact_sheet_path = output_dir / "contact_sheet.jpg"
        create_contact_sheet(slides, contact_sheet_path)

    pdf_path = None
    if options.export_pdf:
        pdf_path = output_dir / f"{safe_stem(lecture_title)}_slides.pdf"
        write_searchable_pdf(
            slides,
            pdf_path,
            add_text_layer=options.add_ocr_layer and not options.no_ocr,
            ocr_layer_mode=options.ocr_layer_mode,
        )

    result = PipelineResult(
        title=lecture_title,
        output_dir=output_dir,
        slides=slides,
        markdown_path=markdown_path,
        manifest_path=output_dir / "slides_manifest.json",
        pdf_path=pdf_path,
        contact_sheet_path=contact_sheet_path,
        video_path=video_path,
    )
    write_manifest(result, source, options)
    return result


def process_url(
    url: str,
    output_root: Path,
    *,
    referer: str | None = None,
    title: str | None = None,
    fetch_page: bool = False,
    cookies_from_browser: str | None = None,
    ffmpeg_location: str | None = None,
    options: ProcessingOptions | None = None,
) -> PipelineResult:
    resolver = SourceResolver()
    source = resolver.resolve(url, referer=referer, title=title, fetch_page=fetch_page)
    if source.local_file:
        output_dir = output_root / safe_stem(source.title or source.local_file.stem)
        return process_video(source.local_file, output_dir, options=options, source=source, title=source.title)

    manager = DownloadManager(ffmpeg_location=ffmpeg_location, cookies_from_browser=cookies_from_browser)
    info = manager.extract_info(source, download=False)
    source.metadata.update(info)
    source.title = title or info.get("title") or source.title or source.video_id or "lecture"
    downloads_dir = output_root / "_videos"
    video_path = manager.download(source, downloads_dir, filename_stem=safe_stem(source.title))
    output_dir = output_root / safe_stem(source.title)
    return process_video(video_path, output_dir, options=options, source=source, title=source.title)
