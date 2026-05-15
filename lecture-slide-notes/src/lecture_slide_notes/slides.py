from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import SlideDetectionOptions, SlideRecord


def require_executable(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"{name} is required on PATH")
    return executable


def sample_frames(video: Path, frames_dir: Path, sample_rate: float, width: int) -> list[Path]:
    ffmpeg = require_executable("ffmpeg")
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = frames_dir / "frame_%06d.jpg"
    vf = f"fps={sample_rate},scale={width}:-1"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vf",
            vf,
            "-q:v",
            "3",
            str(output_pattern),
        ],
        check=True,
    )
    return sorted(frames_dir.glob("frame_*.jpg"))


def capture_frame_at(video: Path, timestamp: float, output_path: Path, width: int = 0) -> None:
    ffmpeg = require_executable("ffmpeg")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf_args = ["-vf", f"scale={width}:-1"] if width and width > 0 else []
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            *vf_args,
            "-compression_level",
            "3",
            str(output_path),
        ],
        check=True,
    )


def average_hash(image_path: Path, hash_size: int = 16) -> int:
    from PIL import Image

    with Image.open(image_path) as image:
        gray = image.convert("L").resize((hash_size, hash_size))
        pixels = list(gray.tobytes())
    average = sum(pixels) / len(pixels)
    bits = 0
    for index, value in enumerate(pixels):
        if value >= average:
            bits |= 1 << index
    return bits


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def frame_index(frame: Path) -> int:
    return int(frame.stem.split("_")[-1])


def timestamp_for_frame(index: int, sample_rate: float) -> float:
    return max(0.0, (index - 1) / sample_rate)


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def build_frame_records(frames: list[Path], sample_rate: float) -> list[dict]:
    return [
        {
            "path": frame,
            "index": frame_index(frame),
            "timestamp": timestamp_for_frame(frame_index(frame), sample_rate),
            "hash": average_hash(frame),
        }
        for frame in frames
    ]


def close_stable_run(run: list[dict], stable_seconds: float) -> dict | None:
    if not run:
        return None
    duration = run[-1]["timestamp"] - run[0]["timestamp"]
    if duration < stable_seconds:
        return None
    return run[len(run) // 2]


def select_stable_slide_frames(frames: list[Path], slides_dir: Path, options: SlideDetectionOptions) -> list[SlideRecord]:
    shutil.rmtree(slides_dir, ignore_errors=True)
    slides_dir.mkdir(parents=True, exist_ok=True)
    records = build_frame_records(frames, options.sample_rate)
    if not records:
        return []

    candidate_runs: list[dict] = []
    run = [records[0]]
    for previous, current in zip(records, records[1:]):
        if hamming(previous["hash"], current["hash"]) <= options.stability_threshold:
            run.append(current)
            continue
        candidate = close_stable_run(run, options.stable_seconds)
        if candidate:
            candidate_runs.append(candidate)
        run = [current]

    candidate = close_stable_run(run, options.stable_seconds)
    if candidate:
        candidate_runs.append(candidate)

    selected: list[SlideRecord] = []
    last_hash: int | None = None
    last_selected_at = -options.min_gap
    for candidate in candidate_runs:
        timestamp = candidate["timestamp"]
        candidate_hash = candidate["hash"]
        if last_hash is not None:
            if timestamp - last_selected_at < options.min_gap:
                continue
            distance = hamming(last_hash, candidate_hash)
            if distance < options.dedupe_threshold:
                continue
            if distance < options.threshold and selected:
                continue

        slide_no = len(selected) + 1
        slide_path = slides_dir / f"slide_{slide_no:03d}.png"
        shutil.copyfile(candidate["path"], slide_path)
        selected.append(
            SlideRecord(
                slide=slide_no,
                timestamp=timestamp,
                timestamp_text=format_timestamp(timestamp),
                file=slide_path,
                source_frame=candidate["path"].name,
            )
        )
        last_hash = candidate_hash
        last_selected_at = timestamp

        if options.max_slides and len(selected) >= options.max_slides:
            break
    return selected


def create_pdf_slide_images(video: Path, slides: list[SlideRecord], pdf_slides_dir: Path, width: int = 0) -> None:
    shutil.rmtree(pdf_slides_dir, ignore_errors=True)
    pdf_slides_dir.mkdir(parents=True, exist_ok=True)
    for slide in slides:
        pdf_path = pdf_slides_dir / f"slide_{slide.slide:03d}.png"
        capture_frame_at(video, slide.timestamp, pdf_path, width=width)
        slide.pdf_file = pdf_path


def create_contact_sheet(slides: list[SlideRecord], output_path: Path, thumb_width: int = 320, columns: int = 4) -> None:
    if not slides:
        return
    from PIL import Image, ImageDraw

    label_height = 34
    thumbs = []
    for slide in slides:
        with Image.open(slide.file) as image:
            rgb = image.convert("RGB")
            thumb_height = int(rgb.height * (thumb_width / rgb.width))
            thumb = rgb.resize((thumb_width, thumb_height))
        canvas = Image.new("RGB", (thumb_width, thumb_height + label_height), "white")
        canvas.paste(thumb, (0, label_height))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, thumb_width, label_height), fill=(245, 245, 245))
        draw.text((8, 8), f"slide_{slide.slide:03d} {slide.timestamp_text}", fill=(0, 0, 0))
        thumbs.append(canvas)

    cell_height = max(thumb.height for thumb in thumbs)
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), (230, 230, 230))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % columns) * thumb_width, (index // columns) * cell_height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=90)


def extract_slides(video: Path, output_dir: Path, options: SlideDetectionOptions) -> list[SlideRecord]:
    if options.sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")
    slides_dir = output_dir / "slides"
    frames_root = output_dir / "_frames" if options.keep_frames else Path(tempfile.mkdtemp(prefix="lecture_frames_"))
    try:
        frames = sample_frames(video, frames_root, options.sample_rate, options.width)
        if not frames:
            raise RuntimeError("No frames were sampled from the video")
        slides = select_stable_slide_frames(frames, slides_dir, options)
        if not slides:
            raise RuntimeError("No slide frames were selected")
        return slides
    finally:
        if not options.keep_frames and frames_root.exists():
            shutil.rmtree(frames_root, ignore_errors=True)
