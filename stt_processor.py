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

        # ── STT 세그먼트로부터 묵음 제거 후 speech-only 오디오 생성 ──────────
        original_duration = len(audio_data) / 16000
        speech_audio, speech_segments = _build_speech_only_audio(audio_data, transcribed_segments)
        speech_duration = len(speech_audio) / 16000
        cb(
            f"묵음 제거 완료: {original_duration:.0f}초 → {speech_duration:.0f}초 "
            f"({speech_duration / original_duration * 100:.0f}% 유지) — "
            "이하 Align·Diarize는 speech-only 오디오 기준으로 처리합니다."
        )

        cb(f"음성 정렬 중 (언어: {info.language})...")
        align_model, metadata = _get_align_model(info.language)
        aligned_result = whisperx.align(
            speech_segments, align_model, metadata, speech_audio, "cpu"
        )

        cb("화자 분리 중 (speech-only 오디오 기준, CPU에서 수 분 소요 가능)...")
        diarize_segments = diarize_model(speech_audio, min_speakers=1, max_speakers=8)

        import pandas as pd
        if isinstance(diarize_segments, pd.DataFrame) and diarize_segments.empty:
            raise RuntimeError("화자 분리 결과가 비어있습니다. 오디오에 발화 구간이 충분하지 않을 수 있습니다.")

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
