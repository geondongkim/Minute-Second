from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable

import numpy as np
import whisperx
from faster_whisper import WhisperModel

# ─── Module-level singletons (replaces @st.cache_resource) ───────────────────
_lock = threading.Lock()
_whisper_model: WhisperModel | None = None
_diarize_model = None          # None = not yet loaded, _LOAD_FAILED = tried + failed
_align_models: dict[str, tuple] = {}
_LOAD_FAILED = object()        # sentinel


def _get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        with _lock:
            if _whisper_model is None:
                _whisper_model = WhisperModel(
                    "small",           # medium 대비 ~2× 빠름, 한국어 정확도 충분
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=os.cpu_count() or 8,   # 논리 코어 전부 활용
                    num_workers=2,
                )
    return _whisper_model


def _get_diarize_model():
    global _diarize_model
    if _diarize_model is None:
        with _lock:
            if _diarize_model is None:
                try:
                    from whisperx.diarize import DiarizationPipeline
                    _diarize_model = DiarizationPipeline(
                        token=os.environ.get("HF_TOKEN", ""),
                        device="cpu",
                    )
                except Exception:
                    _diarize_model = _LOAD_FAILED
    return None if _diarize_model is _LOAD_FAILED else _diarize_model


def _get_align_model(language_code: str) -> tuple:
    if language_code not in _align_models:
        with _lock:
            if language_code not in _align_models:
                _align_models[language_code] = whisperx.load_align_model(
                    language_code=language_code, device="cpu"
                )
    return _align_models[language_code]


def _build_speech_only_audio(
    audio_data: np.ndarray,
    segments: list[dict],
    sample_rate: int = 16000,
    pad_ms: int = 100,
) -> tuple[np.ndarray, list[dict]]:
    """STT 세그먼트 경계만 이어붙인 speech-only 오디오를 생성한다.
    반환값의 타임스탬프는 이어붙인 오디오 기준이며, 원본 기준과 다르다.
    결과 텍스트(회의록)에는 영향 없음 — 타임스탬프 절대값은 불필요."""
    pad = int(pad_ms * sample_rate / 1000)
    chunks: list[np.ndarray] = []
    remapped: list[dict] = []
    cursor = 0.0

    for seg in segments:
        s = max(0, int(seg["start"] * sample_rate) - pad)
        e = min(len(audio_data), int(seg["end"] * sample_rate) + pad)
        chunk = audio_data[s:e]
        chunks.append(chunk)
        duration = len(chunk) / sample_rate
        remapped.append({"start": cursor, "end": cursor + duration, "text": seg["text"]})
        cursor += duration

    if not chunks:
        return audio_data, segments
    return np.concatenate(chunks), remapped


def _emit_progress(
    cb: Callable[[str], None],
    overall: int,
    stage_label: str,
    stage_pct: int,
    elapsed_s: float,
    eta_s: float | None = None,
) -> None:
    """'__PROGRESS__:{json}' 형식으로 프런트엔드에 진행 정보를 전송한다."""
    cb(
        "__PROGRESS__:"
        + json.dumps(
            {
                "overall": max(0, min(100, overall)),
                "stage_label": stage_label,
                "stage_pct": max(0, min(100, stage_pct)),
                "elapsed_s": int(elapsed_s),
                "eta_s": int(eta_s) if eta_s is not None else None,
            },
            ensure_ascii=False,
        )
    )


class _DiarizeTimer:
    """화자 분리(pyannote) 실행 중 2초마다 progress 이벤트를 emit하는 백그라운드 쓰레드.
    pyannote 자체에는 진행률 콜백이 없으므로 경과 시간 + ETA 추정으로 표시한다."""

    def __init__(self, cb: Callable[[str], None], speech_duration_s: float, job_start: float):
        self._cb = cb
        # 경험치: i7-13xx CPU에서 pyannote ≈ speech_duration × 3배 소요
        self._estimated_s = max(speech_duration_s * 3.0, 20.0)
        self._job_start = job_start
        self._stage_start = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._stage_start = time.monotonic()
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(2.0):
            stage_elapsed = time.monotonic() - self._stage_start
            total_elapsed = time.monotonic() - self._job_start
            stage_pct = min(99, int(stage_elapsed / self._estimated_s * 100))
            eta_s = max(0.0, self._estimated_s - stage_elapsed)
            _emit_progress(
                self._cb,
                overall=70 + int(stage_pct * 0.23),  # 70 → 93%
                stage_label="화자 분리 중",
                stage_pct=stage_pct,
                elapsed_s=total_elapsed,
                eta_s=eta_s,
            )


# ─── Public API ───────────────────────────────────────────────────────────────

def process_audio(
    audio_path: str,
    progress_callback: Callable[[str], None] | None = None,
    diarize: bool = True,
) -> tuple[str, str]:
    job_start = time.monotonic()
    model = _get_whisper_model()
    diarize_model = _get_diarize_model() if diarize else None

    def cb(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    def prog(overall: int, stage_label: str, stage_pct: int, eta_s: float | None = None) -> None:
        _emit_progress(cb, overall, stage_label, stage_pct, time.monotonic() - job_start, eta_s)

    # ── 1단계: STT ────────────────────────────────────────────────────────────
    prog(5, "음성 텍스트 변환 중", 0)
    cb("STT 변환 중 (Faster-Whisper)...")
    segments, info = model.transcribe(
        audio_path,
        language="ko",
        beam_size=1,
        best_of=1,
        temperature=0,
        condition_on_previous_text=False,
        word_timestamps=False,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        },
    )

    transcribed_segments: list[dict] = []
    full_text: list[str] = []
    _last_reported = [-5.0]

    for segment in segments:
        full_text.append(segment.text)
        transcribed_segments.append(
            {"start": segment.start, "end": segment.end, "text": segment.text}
        )
        if info.duration > 0 and segment.end - _last_reported[0] >= 5.0:
            _last_reported[0] = segment.end
            stt_pct = segment.end / info.duration * 100
            overall = 5 + int(stt_pct * 0.47)  # 5% → 52%
            cb(f"STT 변환 중: {segment.end:.0f}초 / {info.duration:.0f}초 ({stt_pct:.0f}%)")
            prog(overall, "음성 텍스트 변환 중", int(stt_pct))

    combined_text = " ".join(full_text)
    prog(52, "전사 완료", 100)
    cb("전사 완료.")

    if not diarize:
        prog(100, "완료", 100)
        plain_lines = "\n".join(f"- {seg['text'].strip()}" for seg in transcribed_segments)
        return combined_text, plain_lines

    try:
        if diarize_model is None:
            raise RuntimeError(
                "화자 분리 모델 로드 실패 — HF_TOKEN이 없거나 pyannote 접근 권한이 없습니다."
            )

        # ── 2단계: 묵음 제거 ─────────────────────────────────────────────────
        prog(54, "오디오 로드 및 묵음 제거 중", 20)
        cb("오디오 데이터 로드 중...")
        audio_data: np.ndarray = whisperx.load_audio(audio_path)

        original_duration = len(audio_data) / 16000
        speech_audio, speech_segments = _build_speech_only_audio(audio_data, transcribed_segments)
        speech_duration = len(speech_audio) / 16000
        prog(57, "묵음 제거 완료", 100)
        cb(
            f"묵음 제거: {original_duration:.0f}초 → {speech_duration:.0f}초 "
            f"({speech_duration / original_duration * 100:.0f}% 유지)"
        )

        # ── 3단계: 음성 정렬 ─────────────────────────────────────────────────
        prog(59, "음성 정렬 중", 10)
        cb(f"음성 정렬 중 (언어: {info.language})...")
        align_model, metadata = _get_align_model(info.language)
        aligned_result = whisperx.align(
            speech_segments, align_model, metadata, speech_audio, "cpu"
        )
        prog(70, "음성 정렬 완료", 100)

        # ── 4단계: 화자 분리 ─────────────────────────────────────────────────
        eta_diarize = speech_duration * 3.0
        prog(70, "화자 분리 준비", 0, eta_diarize)
        cb(f"화자 분리 중... (예상 소요: 약 {eta_diarize / 60:.0f}분)")
        with _DiarizeTimer(cb, speech_duration, job_start):
            diarize_segments = diarize_model(speech_audio, min_speakers=1, max_speakers=8)

        prog(93, "화자 배정 중", 80)
        import pandas as pd
        if isinstance(diarize_segments, pd.DataFrame) and diarize_segments.empty:
            raise RuntimeError("화자 분리 결과가 비어있습니다. 오디오에 발화 구간이 충분하지 않을 수 있습니다.")

        result = whisperx.assign_word_speakers(diarize_segments, aligned_result)

        speaker_lines = [
            f"[{seg.get('speaker', 'Unknown')}] {seg.get('text', '').strip()}"
            for seg in result["segments"]
        ]
        full_speaker_text = "\n".join(speaker_lines)
        prog(94, "화자 분리 완료", 100)

    except Exception as exc:
        prog(94, "화자 분리 실패", 100)
        full_speaker_text = (
            f"[화자 분리 실패: {exc}]\n\n"
            + "\n".join(f"- {seg['text']}" for seg in transcribed_segments)
        )

    return combined_text, full_speaker_text
