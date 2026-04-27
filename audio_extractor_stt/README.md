# Minute Second - Audio Extractor STT

동영상 파일을 업로드하면 오디오 추출, STT, 화자 분리, AI 회의록 생성을 한 번에 처리하는 FastAPI + React 서비스입니다.

## 주요 기능

- MP4, MKV, AVI, MOV 등 동영상 파일 업로드
- FFmpeg 기반 16 kHz mono WAV 오디오 추출
- Faster-Whisper 기반 한국어 STT
- WhisperX + pyannote 기반 화자 분리
- Gemini API 기반 회의 유형별 요약
- SSE 기반 실시간 진행 로그와 진행률 표시
- AI 요약, 화자별 스크립트, 전체 원문 다운로드

## 요구 사항

- Python 3.10+
- uv
- Node.js 18+
- npm
- FFmpeg
- Gemini API key
- Hugging Face token, optional for speaker diarization

## 환경 변수

`audio_extractor_stt/.env` 파일을 만듭니다.

```dotenv
MINUTE_SECOND_API_KEY=your_gemini_api_key
HF_TOKEN=your_huggingface_token
```

`HF_TOKEN`이 없으면 화자 분리는 건너뛰고 STT와 요약 중심으로 동작합니다.

## 설치

백엔드 의존성:

```powershell
cd audio_extractor_stt
uv sync
```

프론트엔드 의존성:

```powershell
cd audio_extractor_stt/frontend
npm install
```

## 개발 서버 실행

터미널 1, FastAPI 백엔드:

```powershell
cd audio_extractor_stt
uv run uvicorn main:app --reload --port 8000
```

터미널 2, React/Vite 프론트엔드:

```powershell
cd audio_extractor_stt/frontend
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

## 프로덕션 형태 실행

React 앱을 빌드한 뒤 FastAPI에서 정적 파일로 함께 제공합니다.

```powershell
cd audio_extractor_stt/frontend
npm run build
cd ..
uv run uvicorn main:app --port 8000
```

브라우저에서 `http://localhost:8000`으로 접속합니다.

## CLI 사용

서버 없이 파일 하나를 직접 처리할 수 있습니다.

```powershell
cd audio_extractor_stt
uv run python run_cli.py "videos/meeting.mp4"
```

기본 결과는 `results/` 아래 Markdown 파일로 저장됩니다.

## API 요약

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/jobs` | 동영상 업로드 및 처리 작업 생성 |
| `GET` | `/api/jobs/{job_id}/events` | SSE 진행 로그 스트림 |
| `GET` | `/api/jobs/{job_id}/result` | 처리 완료 결과 조회 |

## 주요 파일

| 파일 | 역할 |
|---|---|
| `main.py` | FastAPI 앱, 업로드, 작업 상태, SSE, 결과 API |
| `audio_extractor.py` | FFmpeg 오디오 추출 |
| `stt_processor.py` | Faster-Whisper STT와 WhisperX 화자 분리 |
| `summarizer.py` | Gemini 요약 프롬프트와 API 호출 |
| `run_cli.py` | 배치 처리용 CLI |
| `frontend/src/api.ts` | 프론트엔드 API 클라이언트 |
| `frontend/src/App.tsx` | 업로드-처리-결과 상태 흐름 |
| `frontend/src/components/` | 업로드, 진행 로그, 결과 탭 UI |

## 검증

프론트엔드 변경 후:

```powershell
cd audio_extractor_stt/frontend
npm run lint
npm run build
```

백엔드 변경 후에는 변경 범위에 맞춰 import smoke test, CLI 실행, 또는 FastAPI 서버 실행을 확인합니다.

## 참고 문서

- `../docs/audio-extractor-stt.md`
- `../docs/development-guide.md`
- `../docs/architecture.md`
