# Minute_Second — Implementation Plan

## 개요
동영상 파일 업로드 → 오디오 추출 → STT(화자 분리 포함) → AI 요약 자동 회의록 생성.
**CPU 전용** 로컬 환경, Windows 11.

---

## 현재 아키텍처 (v2 — FastAPI + React)

### 백엔드: FastAPI (`main.py`)
| 엔드포인트 | 설명 |
|---|---|
| `POST /api/jobs` | 동영상 업로드(1 MB 청크) → 비동기 처리 시작 |
| `GET /api/jobs/{id}/events` | SSE 스트림 (실시간 진행 메시지) |
| `GET /api/jobs/{id}/result` | JSON 결과 (summary, speaker_text, combined_text) |

- **`asyncio.to_thread`**: CPU-bound STT/요약을 스레드풀에서 실행 (이벤트루프 비차단)
- **`threading.Lock` (double-checked locking)**: 모델 싱글톤 스레드 안전 초기화
- **SSE 프로토콜**: `__DONE__` / `__ERROR__:<msg>` 센티넬

### 프론트엔드: React 19 + Vite 8 + TypeScript (`frontend/`)
- State machine: `idle → uploading → processing → done | error`
- **XHR 업로드**: `fetch`는 업로드 진행률 지원 안 함 → XMLHttpRequest 사용
- **EventSource SSE**: `/api/jobs/{id}/events` 연결 → 실시간 로그 표시
- **3-tab 결과**: 📌 회의 요약(ReactMarkdown), 🗣️ 화자별 스크립트, 📄 전체 원문
- **회의 유형 선택**: UploadZone에서 10개 유형 선택 → 백엔드 summarizer에 전달
- **참고자료 첨부**: MD/TXT 파일 첨부 → 요약 프롬프트에 포함
- **다운로드 버튼**: 모든 탭에서 MD/TXT 파일로 저장 가능

---

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `main.py` | FastAPI 앱, 잡 관리, SSE |
| `run_cli.py` | CLI 파이프라인 (argparse, 터미널 게이지, `.md` 저장) |
| `stt_processor.py` | Faster-Whisper + WhisperX 화자 분리 |
| `audio_extractor.py` | ffmpeg 오디오 추출 (sync + async 버전) |
| `summarizer.py` | Gemini API 요약 |
| `frontend/src/App.tsx` | React 상태 머신 |
| `frontend/src/api.ts` | createJob / subscribeJobEvents / fetchJobResult |
| `frontend/src/components/` | UploadZone, ProgressLog, ResultTabs |

---

## CLI 사용법 (`run_cli.py`)

```powershell
# 단일 파일 처리
uv run python run_cli.py "videos/회의.mp4"

# 출력 디렉터리 지정
uv run python run_cli.py "videos/회의.mp4" --output-dir "output/"
```

- 결과: `results/<파일명>_<YYYYmmdd_HHMMSS>.md`
- 구성: AI 요약(Gemini) + 화자별 스크립트 + 전체 원문(STT)
- 터미널 게이지: `[████░░] 45%  화자 분리 중 (20%)  ETA 2분 30초`

---

## 개발 서버 실행

```powershell
# 터미널 1 — FastAPI 백엔드
uv run uvicorn main:app --reload --port 8000

# 터미널 2 — React 개발 서버 (핫 리로드)
cd frontend
npm run dev   # → http://localhost:5173
```

프로덕션 빌드:
```powershell
cd frontend ; npm run build   # frontend/dist/ 생성
uv run uvicorn main:app --port 8000   # /assets 및 SPA fallback 서빙
```

---

## 환경 변수 (`.env`)

| 변수 | 설명 |
|---|---|
| `HF_TOKEN` | Hugging Face token (화자 분리 모델용) |
| `MINUTE_SECOND_API_KEY` | Gemini API 키 |

---

## 알려진 제약 / 주의사항

- **torchcodec**: Windows에서 `pyannote-audio 4.x`가 요구 → `pyproject.toml`의 `override-dependencies`로 차단
- **화자 분리 모델**: `HF_TOKEN` 없으면 graceful degradation (텍스트만 출력)
- **단일 사용자**: 동시 요청 처리 불필요. in-memory job store 사용
- **파일 크기**: 청크 업로드로 대용량(2 GB+) 지원

---

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1 | 초기 | Streamlit 기반 구현 |
| v1.1 | - | @st.cache_resource 모델 캐싱, whisperX 화자분리 통합 |
| v1.2 | - | torchcodec DLL 오류 수정, 진행률 콜백 추가 |
| v2 | 현재 | FastAPI + React 완전 이관, SSE 실시간 진행, 비동기 최적화 |
| v2.1 | 현재 | STT 최적화 (small 모델, greedy, VAD, silence pre-cut), 실시간 게이지 + ETA |
| v2.2 | 현재 | `run_cli.py` CLI 스크립트 추가 (argparse, 터미널 게이지, `results/` 자동 저장) |
