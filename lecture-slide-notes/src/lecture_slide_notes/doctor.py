from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_executable(name: str) -> CheckResult:
    path = shutil.which(name)
    return CheckResult(name=name, ok=bool(path), detail=path or "not found on PATH")


def check_module(name: str) -> CheckResult:
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    return CheckResult(name=name, ok=bool(spec), detail="installed" if spec else "not installed")


def run_checks() -> list[CheckResult]:
    checks = [
        check_executable("ffmpeg"),
        check_executable("ffprobe"),
        check_executable("tesseract"),
        check_module("yt_dlp"),
        check_module("PIL"),
        check_module("reportlab"),
        check_module("fitz"),
        check_module("google.genai"),
        check_module("pytesseract"),
    ]
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    checks.append(CheckResult(name="Gemini API key", ok=bool(api_key), detail="set" if api_key else "not set"))
    return checks
