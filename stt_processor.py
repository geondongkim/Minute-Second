from __future__ import annotations

import os
import threading
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


# ─── Public API ───────────────────────────────────────────────────────────────

def process_audio(
    audio_path: str,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    model = _get_whisper_model()
    diarize_model = _get_diarize_model()

    def cb(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    cb("STT 변환 중 (Faster-Whisper)...")
    segments, info = model.transcribe(
        audio_path,
        language="ko",                    # 언어 감지 건너뜀 (~5초 절약)
        beam_size=1,                      # greedy 디코딩 — beam search 대비 3–5× 빠름
        best_of=1,                        # 후보 생성 최소화
        temperature=0,                    # 결정론적 출력 (재샘플링 없음)
        condition_on_previous_text=False, # 세그먼트 간 컨텍스트 의존 제거
        word_timestamps=False,            # whisperX 정렬이 따로 처리하므로 불필요
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,  # 기본 2000ms → 무음 구간 압축
            "speech_pad_ms": 200,            # 기본 400ms → 패딩 절반 축소
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
            pct = segment.end / info.duration * 100
            cb(f"STT 변환 중: {segment.end:.0f}초 / {info.duration:.0f}초 ({pct:.0f}%)")

    combined_text = " ".join(full_text)
    cb("전사 완료. 오디오 정렬 준비 중...")

    try:
        if diarize_model is None:
            raise RuntimeError(
                "화자 분리 모델 로드 실패 — HF_TOKEN이 없거나 pyannote 접근 권한이 없습니다."
            )

        cb("오디오 데이터 로드 중...")
        audio_data: np.ndarray = whisperx.load_audio(audio_path)

        cb(f"음성 정렬 중 (언어: {info.language})...")
        align_model, metadata = _get_align_model(info.language)
        aligned_result = whisperx.align(
            transcribed_segments, align_model, metadata, audio_data, "cpu"
        )

        cb("화자 분리 중 (CPU에서 수 분 소요될 수 있습니다)...")
        diarize_segments = diarize_model(audio_data)
        result = whisperx.assign_word_speakers(diarize_segments, aligned_result)

        speaker_lines = [
            f"[{seg.get('speaker', 'Unknown')}] {seg.get('text', '').strip()}"
            for seg in result["segments"]
        ]
        full_speaker_text = "\n".join(speaker_lines)

    except Exception as exc:
        full_speaker_text = (
            f"[화자 분리 실패: {exc}]\n\n"
            + "\n".join(f"- {seg['text']}" for seg in transcribed_segments)
        )

    return combined_text, full_speaker_text
