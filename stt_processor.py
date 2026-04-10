import streamlit as st
import whisperx
from faster_whisper import WhisperModel
import os
import numpy as np

@st.cache_resource
def _load_whisper_model():
    """Faster-Whisper 모델 1회 로드 후 캐시."""
    return WhisperModel(
        "medium",
        device="cpu",
        compute_type="int8",
        cpu_threads=8,
        num_workers=2,
    )

@st.cache_resource
def _load_diarize_model():
    """PyAnnote 화자 분리 모델 1회 로드 후 캐시."""
    try:
        from whisperx.diarize import DiarizationPipeline
        return DiarizationPipeline(
            token=os.environ.get("HF_TOKEN", ""),
            device="cpu",
        )
    except Exception as e:
        return None

@st.cache_resource
def _load_align_model(language_code: str):
    """언어별 WhisperX alignment 모델 1회 로드 후 캐시."""
    return whisperx.load_align_model(language_code=language_code, device="cpu")


def process_audio(audio_path: str, progress_callback=None):
    model = _load_whisper_model()
    diarize_model = _load_diarize_model()

    if progress_callback:
        progress_callback("STT 변환 중 (Faster-Whisper)...")

    segments, info = model.transcribe(audio_path, vad_filter=True)

    transcribed_segments = []
    full_text = []
    # progress callback 빈도 제한: 마지막 콜백으로부터 5초 이상 진행 시에만 갱신
    _last_reported = [-5.0]
    for segment in segments:
        full_text.append(segment.text)
        transcribed_segments.append(
            {"start": segment.start, "end": segment.end, "text": segment.text}
        )
        if progress_callback and info.duration > 0:
            if segment.end - _last_reported[0] >= 5.0:
                _last_reported[0] = segment.end
                pct = segment.end / info.duration * 100
                progress_callback(
                    f"STT 변환 중: {segment.end:.0f}초 / {info.duration:.0f}초 ({pct:.0f}%)"
                )

    combined_text = " ".join(full_text)

    if progress_callback:
        progress_callback("전사 완료. 오디오 정렬(alignment) 준비 중...")

    try:
        if diarize_model is None:
            raise RuntimeError(
                "화자 분리 모델 로드 실패 - HF_TOKEN이 없거나 pyannote 접근 권한이 없습니다."
            )

        # 오디오를 numpy array로 1회 로드 (재사용)
        if progress_callback:
            progress_callback("오디오 데이터 로드 중...")
        audio_data: np.ndarray = whisperx.load_audio(audio_path)

        # alignment: 언어별 캐시된 모델 사용
        if progress_callback:
            progress_callback(f"음성 정렬 중 (언어: {info.language})...")
        align_model, metadata = _load_align_model(info.language)
        aligned_result = whisperx.align(
            transcribed_segments, align_model, metadata, audio_data, "cpu"
        )

        # diarization: pre-loaded numpy array 전달 (torchcodec 사용 안 함)
        if progress_callback:
            progress_callback("화자 분리 중 (CPU에서 수 분 소요될 수 있습니다)...")
        diarize_segments = diarize_model(audio_data)
        result = whisperx.assign_word_speakers(diarize_segments, aligned_result)

        speaker_lines = []
        for seg in result["segments"]:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "").strip()
            speaker_lines.append(f"[{speaker}] {text}")

        full_speaker_text = "\n".join(speaker_lines)

    except Exception as e:
        # 화자 분리 실패 시 원문 그대로 반환 (STT 결과는 보존)
        full_speaker_text = (
            f"[화자 분리 실패: {e}]\n\n"
            + "\n".join(f"- {seg['text']}" for seg in transcribed_segments)
        )

    return combined_text, full_speaker_text
