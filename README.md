# Minute Second

동영상 파일을 업로드하면 오디오를 추출하고, 음성을 텍스트로 변환한 뒤, LLM으로 회의록을 자동 생성하는 Streamlit 웹 서비스입니다.

## 기능

- **동영상 업로드**: MP4 파일 업로드 (최대 2GB)
- **오디오 추출**: FFmpeg로 WAV 변환 (16kHz, 모노)
- **음성 인식 (STT)**: WhisperX + 화자 분리 (pyannote.audio)
- **회의록 요약**: Gemini API (`gemini-3.1-flash-lite-preview`)

## 실행 방법

```bash
# 환경 변수 설정 (.env 파일)
GEMINI_API_KEY=your_key_here
HF_TOKEN=your_huggingface_token_here

# 앱 실행
uv run streamlit run app.py
```

## 요구 사항

- Python 3.10+
- FFmpeg (PATH에 등록)
- GEMINI_API_KEY, HF_TOKEN

## 프로젝트 구조

```
app.py              # Streamlit UI
audio_extractor.py  # FFmpeg 오디오 추출
stt_processor.py    # WhisperX STT + 화자 분리
summarizer.py       # Gemini API 요약
```
