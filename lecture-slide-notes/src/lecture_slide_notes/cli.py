from __future__ import annotations

import argparse
import json
from pathlib import Path

from .doctor import run_checks
from .models import ProcessingOptions, SlideDetectionOptions
from .pipeline import process_url, process_video
from .serialization import to_jsonable
from .sources import SourceResolver


def add_processing_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sample-rate", type=float, default=2.0)
    parser.add_argument("--min-gap", type=float, default=8.0)
    parser.add_argument("--threshold", type=int, default=22)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--pdf-width", type=int, default=0)
    parser.add_argument("--stable-seconds", type=float, default=2.0)
    parser.add_argument("--stability-threshold", type=int, default=10)
    parser.add_argument("--dedupe-threshold", type=int, default=18)
    parser.add_argument("--max-slides", type=int, default=0)
    parser.add_argument("--keep-frames", action="store_true")
    parser.add_argument("--no-contact-sheet", action="store_true")
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--no-ocr-layer", action="store_true")
    parser.add_argument("--ocr-layer-mode", choices=("hidden", "invisible"), default="hidden")
    parser.add_argument("--ocr-lang", default="kor+eng")
    parser.add_argument("--gemini-correct", action="store_true")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash")
    parser.add_argument("--gemini-api-key", default=None)


def options_from_args(args: argparse.Namespace) -> ProcessingOptions:
    detection = SlideDetectionOptions(
        sample_rate=args.sample_rate,
        min_gap=args.min_gap,
        threshold=args.threshold,
        width=args.width,
        pdf_width=args.pdf_width,
        stable_seconds=args.stable_seconds,
        stability_threshold=args.stability_threshold,
        dedupe_threshold=args.dedupe_threshold,
        max_slides=args.max_slides,
        keep_frames=args.keep_frames,
        create_contact_sheet=not args.no_contact_sheet,
    )
    return ProcessingOptions(
        detection=detection,
        export_pdf=not args.no_pdf,
        add_ocr_layer=not args.no_ocr_layer,
        ocr_layer_mode=args.ocr_layer_mode,
        ocr_lang=args.ocr_lang,
        no_ocr=args.no_ocr,
        correct_with_gemini=args.gemini_correct,
        gemini_model=args.gemini_model,
        gemini_api_key=args.gemini_api_key,
    )


def print_result(result) -> None:
    print(f"Slides: {len(result.slides)}")
    print(f"Output: {result.output_dir}")
    print(f"Markdown: {result.markdown_path}")
    if result.pdf_path:
        print(f"PDF: {result.pdf_path}")
    if result.contact_sheet_path:
        print(f"Contact sheet: {result.contact_sheet_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build slide notes from Vimeo, YouTube, course URLs, or local video files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local dependencies")
    doctor.set_defaults(func=cmd_doctor)

    resolve = subparsers.add_parser("resolve", help="Resolve a URL or capture JSON into source metadata")
    resolve.add_argument("source")
    resolve.add_argument("--referer")
    resolve.add_argument("--title")
    resolve.add_argument("--fetch-page", action="store_true")
    resolve.set_defaults(func=cmd_resolve)

    process_video_parser = subparsers.add_parser("process-video", help="Process a local video file")
    process_video_parser.add_argument("video", type=Path)
    process_video_parser.add_argument("--output", type=Path, required=True)
    process_video_parser.add_argument("--title")
    add_processing_args(process_video_parser)
    process_video_parser.set_defaults(func=cmd_process_video)

    process_url_parser = subparsers.add_parser("process-url", help="Download and process a Vimeo/YouTube/course URL")
    process_url_parser.add_argument("url")
    process_url_parser.add_argument("--output-root", type=Path, required=True)
    process_url_parser.add_argument("--referer")
    process_url_parser.add_argument("--title")
    process_url_parser.add_argument("--fetch-page", action="store_true")
    process_url_parser.add_argument("--cookies-from-browser", help="Example: chrome or edge:Profile 1")
    process_url_parser.add_argument("--ffmpeg-location")
    add_processing_args(process_url_parser)
    process_url_parser.set_defaults(func=cmd_process_url)

    batch = subparsers.add_parser("batch", help="Process a JSON batch file")
    batch.add_argument("batch_file", type=Path)
    batch.add_argument("--output-root", type=Path, required=True)
    batch.add_argument("--cookies-from-browser")
    batch.add_argument("--ffmpeg-location")
    add_processing_args(batch)
    batch.set_defaults(func=cmd_batch)

    return parser


def cmd_doctor(_: argparse.Namespace) -> int:
    failed = False
    for check in run_checks():
        marker = "OK" if check.ok else "MISS"
        print(f"[{marker}] {check.name}: {check.detail}")
        failed = failed or not check.ok and check.name in {"ffmpeg", "ffprobe", "yt_dlp", "PIL", "reportlab"}
    return 1 if failed else 0


def cmd_resolve(args: argparse.Namespace) -> int:
    source = SourceResolver().resolve(args.source, referer=args.referer, title=args.title, fetch_page=args.fetch_page)
    print(json.dumps(to_jsonable(source), ensure_ascii=False, indent=2))
    return 0


def cmd_process_video(args: argparse.Namespace) -> int:
    result = process_video(args.video, args.output, options=options_from_args(args), title=args.title)
    print_result(result)
    return 0


def cmd_process_url(args: argparse.Namespace) -> int:
    result = process_url(
        args.url,
        args.output_root,
        referer=args.referer,
        title=args.title,
        fetch_page=args.fetch_page,
        cookies_from_browser=args.cookies_from_browser,
        ffmpeg_location=args.ffmpeg_location,
        options=options_from_args(args),
    )
    print_result(result)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    entries = json.loads(args.batch_file.read_text(encoding="utf-8"))
    if isinstance(entries, dict):
        entries = entries.get("lectures", [])
    if not isinstance(entries, list):
        raise ValueError("Batch file must be a JSON list or an object with a lectures list")

    options = options_from_args(args)
    for entry in entries:
        result = process_url(
            entry["url"],
            args.output_root,
            referer=entry.get("referer"),
            title=entry.get("title"),
            fetch_page=entry.get("fetch_page", False),
            cookies_from_browser=entry.get("cookies_from_browser") or args.cookies_from_browser,
            ffmpeg_location=args.ffmpeg_location,
            options=options,
        )
        print_result(result)
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
