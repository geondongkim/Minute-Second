# Minute_Second Execution Plan

## 목표
Streamlit 기반 '동영상 파일 업로드 -> 오디오 추출 -> STT 처리 -> LLM 요약' 자동 회의록 웹 서비스 개발.
GPU가 없는 로컬 CPU 환경을 고려하여 최적화 및 안정성 확보.

## User Review Required
- `faster-whisper`와 `WhisperX`의 의존성 설치 구성을 확인 부탁드립니다. Windows CPU 환경에서 특정 패키지(예: torch, torchaudio) 설치가 까다로울 수 있습니다.
- 대용량 파일 업로드 시 Streamlit의 `server.maxUploadSize`를 적절히 상향 설정해야 업로드가 실패하지 않습니다. 기본값은 200MB이므로, 2GB 수준으로 올리는 방안을 제안합니다.
- Gemini API 버전: `google-genai` SDK를 사용하고 `.env`에서 `MINUTE_SECOND_API_KEY`를 로드해야 합니다.

## Proposed Changes

### 1. Configuration & Setup
#### [NEW] `requirements.txt`
의존성 패키지 명세: `streamlit`, `ffmpeg-python`, `faster-whisper`, `whisperx`, `google-genai`, `python-dotenv`, `pydub`(또는 chunking용 라이브러리).
#### [MODIFY] `.env`
`.env` 파일에 `MINUTE_SECOND_API_KEY` 키 형식을 추가하여 환경 변수를 관리하도록 안내 (키 자체는 하드코딩하지 않음).
#### [NEW] `.streamlit/config.toml`
대용량 파일 업로드를 위해 `server.maxUploadSize` 값을 늘려 설정.

### 2. Core Processing Modules
#### [NEW] `audio_extractor.py`
- `tempfile`을 사용하여 업로드된 비디오를 저장하고 `ffmpeg-python`으로 오디오 데이터를 추출(16kHz, mono, wav).
- Streamlit의 임시 상태가 끝나면 파일들을 적절히 삭제(cleanup)하는 컨텍스트 매니저 혹은 함수 제공.

#### [NEW] `stt_processor.py`
- `faster-whisper` 모델 캐싱 (`@st.cache_resource`).
  - 초기화 파라미터: `model_size="medium"`, `device="cpu"`, `compute_type="int8"`, `cpu_threads=8`, `num_workers=2`.
- `transcribe(audio, vad_filter=True)` 실행.
- 대용량 오디오의 경우 chunk 단위로 분할하여 STT하는 스트리밍 로직 적용 (메모리 부족 방지).
- **WhisperX Diarization**: 추출된 text segments 기반으로 GPU 없이 CPU 모드(`device="cpu"`)에서 화자 분리 진행.

#### [NEW] `summarizer.py`
- `google-genai` SDK 연결. `os.environ.get('MINUTE_SECOND_API_KEY')` 활용.
- 모델: `gemini-3.1-flash-lite-preview`.
- Prompt Template 구성:
  - "주요 안건"
  - "핵심 논의 내용"
  - "Action Item(담당자 및 기한)"
- 모델 호출 및 스트리밍 응답 또는 즉각적 응답 반환.

### 3. Frontend Application
#### [NEW] `app.py`
- Streamlit 메인 UI 로직 구성.
- 사이드바 또는 메인 창에서 파일 업로드 처리.
- `st.progress` 및 `st.spinner`로 상태 표시 ("동영상 업로드 완료" -> "오디오 추출 중" -> "STT 텍스트 변환 중" -> "요약 작성 중").
- 결과 화면 출력 (전체 텍스트, 화자별 텍스트, 요약 Markdown).

## Verification Plan
### Automated & Unit Testing
- 로컬 비디오(.mp4 파일) 등을 사용한 오디오 추출 테스트.
- 특정 오디오의 STT 및 화자 분리 결과 테스트.
- 빈 입력 또는 잘못된 포맷의 파일 업로드 시 에러 핸들링 점검 (`try-except` 블록).

### Manual Verification
1. `streamlit run app.py`를 실행하여 500MB 이상의 비디오 파일 업로드.
2. 페이지 튕김/새로고침 현상이 없는지 확인, `st.progress` 상태창이 정상 동작하는지 확인.
3. 처리 중 `tempfile`이 잘 지워지는지, 메모리 누수가 없는지 리소스 모니터로 확인 (특히 STT 단계).
4. 결과물에 주요 안건, 핵심 논의 내용, Action Item이 마크다운 형식으로 명확히 도출되는지 확인.

## Bug Fixes & Root Cause Analysis (2026-04-10)

### 수정된 근본 문제들

#### 1. `torchcodec` — Windows CPU 환경에서 DLL 로드 실패
- **근본 원인**: `torchcodec`이 설치됐지만 Windows에서 FFmpeg "full-shared" DLL(`libtorchcodec_core4~8.dll`)이 없어 5개 FFmpeg 버전 각각에 대한 대형 오류 블록이 매 실행마다 출력됐음.
- **수정**: `pyproject.toml`에서 `torchcodec` 의존성 제거 + `.venv`에서 uninstall.
- **근거**: `pyannote.audio`의 `DiarizationPipeline`은 우리 코드에서 이미 `{'waveform': tensor, 'sample_rate': int}` dict로 오디오를 전달하므로 torchcodec을 실제로 사용하지 않음.

#### 2. `gemini-3.1-flash-lite` — 모델명 오류
- **근본 원인**: `summarizer.py`에서 `-preview` suffix 없는 `gemini-3.1-flash-lite`를 사용해 매 요약마다 API 오류 후 fallback 발생.
- **수정**: `gemini-3.1-flash-lite` → `gemini-3.1-flash-lite-preview` (실제 존재하는 모델명으로 수정).

#### 3. `load_align_model` — 언어별 캐싱 없음
- **근본 원인**: `process_audio()` 호출마다 `whisperx.load_align_model()`이 HuggingFace에서 매번 재로드됨.
- **수정**: `@st.cache_resource`를 적용한 `_load_align_model(language_code)` 함수로 분리해 1회 로드 후 캐싱.

#### 4. progress callback 과도한 호출
- **근본 원인**: STT 세그먼트마다 콜백을 호출해 1454초 영상에서 ~500회 `status_text.write()` 실행 → Streamlit UI 과부하.
- **수정**: 마지막 콜백으로부터 5초 이상 진행된 경우에만 갱신하도록 throttle 적용.

#### 5. 모델 로딩 구조 개선
- **근본 원인**: `load_stt_resources()`에 Whisper + Diarize 모델이 묶여 있어 둘 중 하나 실패 시 모두 재로드됨.
- **수정**: `_load_whisper_model()`, `_load_diarize_model()`, `_load_align_model(lang)` 3개로 분리해 독립 캐싱.

## Bug Fixes — uv run 의존성 충돌 해결 (2026-04-11)

### 문제
`uv run streamlit run app.py` 실행 시 `torch` 패키지에 대한 인덱스 충돌:
```
Requirements contain conflicting indexes for package `torch` in all marker environments:
- https://download.pytorch.org/whl/cpu
- https://download.pytorch.org/whl/cu128
```

### 근본 원인
whisperX `pyproject.toml`의 `[tool.uv.sources]`에 Windows x86_64 환경에서 `torch`를 `cu128` (CUDA) 인덱스에서 해결하도록 설정되어 있었음. uv 0.11.1은 root project의 sources가 git-sourced 의존성의 sources를 재정의하지 않고 병합함 → CPU/CUDA 두 인덱스 동시 요구 → 충돌.

### 해결 방법
1. **whisperX를 git URL → 로컬 경로 참조로 변경**: `ref/whisperX/` 로컬 사본을 수정하여 완전한 제어권 확보.
2. **`ref/whisperX/pyproject.toml` 수정**:
   - `[tool.uv.sources]`: marker-based 인덱스 제거 → `{ index = "pytorch-cpu" }` 단순화
   - `[[tool.uv.index]]`: cu128 인덱스 완전 제거
   - `torchcodec` 의존성: `sys_platform == 'win32'` 조건 제거 (Windows DLL 오류 방지)
3. **root `pyproject.toml` 변경**:
   - `whisperx @ git+https://...` → `whisperx>=3.8.5` + `[tool.uv.sources] whisperx = { path = "./ref/whisperX" }`
   - `[tool.uv] package = false` 추가 (Streamlit 앱은 Python 패키지가 아님 — hatchling 빌드 불필요)
4. **검증**: `uv sync` Exit code: 0, `uv run python -c "import whisperx; import torch" → OK 2.8.0+cpu`
