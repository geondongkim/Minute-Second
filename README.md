# Minute Second

> 두 개의 독립 서비스로 구성된 AI 기반 회의록 자동화 도구 모음

| 디렉터리 | 설명 |
|---|---|
| `audio_extractor_stt/` | 동영상 → 오디오 추출 → STT → 회의록 웹 서비스 (FastAPI + React + WhisperX + Gemini) |
| `teams-caption-saver/` | MS Teams 실시간 자막 캡처 + AI 요약 Chrome/Edge 확장 MV3 |

---

## Teams Captions Saver KR (`teams-caption-saver/`)

MS Teams 라이브 캡션을 자동 저장·요약하는 Chrome/Edge 확장 v2.0.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 실시간 캡처 | MutationObserver로 Teams 자막 DOM 감지, 발화 완료 시 저장 |
| 자막 자동 켜기 | 회의 참여 시 라이브 캡션 자동 활성화 |
| 참석자 추적 | 참석자 목록 실시간 추적 및 보고서 생성 |
| 자동 저장 | 5분 주기 + 회의 종료 시 자동 저장 |
| 다양한 포맷 | Markdown / TXT / JSON 선택 저장 |
| 발화자 별칭 | 이름 치환 기능 |
| AI 요약 | Gemini / OpenAI API 기반, 10개 회의 유형별 프롬프트 |
| 실시간 뷰어 | 3탭 뷰어 — 원문 / 발화자별 / AI 요약 (참고파일 첨부 지원) |
| 세션 히스토리 | 최근 10회 세션 저장 및 다시 보기 |
| 사이드바 모드 | Chrome Side Panel API — 팝업 대신 우측 사이드바로 사용 가능 |

### 설치

1. `teams-caption-saver/` 폴더를 Chrome/Edge `chrome://extensions/` → **압축 해제된 확장 로드**로 등록
2. Manifest V3 · Chrome 114+ 필요 (Side Panel API)

### UI 구성

**팝업 / 사이드바 — 4탭**

- **캡처**: 현재 상태, 문장 수 / 경과 / 참석자, 지금 저장, 뷰어 열기, 자동저장 토글
- **설정**: 자막 자동 켜기, 회의 종료 시 자동 저장, 참석자 추적, 포맷, 폴더, 발화자 별칭
- **AI 요약**: Gemini / OpenAI API 키 입력, 모델 선택, 회의 유형별 / 커스텀 프롬프트
- **히스토리**: 세션 목록 → 클릭 시 뷰어에서 다시 보기

**뷰어 (`viewer.html`) — 3탭**

- **📄 원문**: 발화자 필터 + 검색 + 자막 목록 (LIVE 실시간 업데이트)
- **🗣️ 발화자별**: 발화자 그룹별 대화 목록
- **📌 AI 요약**: AI 설정 (편집 가능) + 회의유형 선택 + 참고파일 첨부 (MD / TXT / PDF) + 3섹션 결과

---

## Minute Second 웹 서비스 (`audio_extractor_stt/`)

동영상 파일 업로드 → 오디오 추출 → STT + 화자 분리 → AI 요약 회의록 자동 생성.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 동영상 업로드 | MP4 / MKV / AVI / MOV · 최대 2 GB (1 MB 청크 스트리밍) |
| 오디오 추출 | FFmpeg — 16kHz / 모노 WAV 변환 (비동기, 논블로킹) |
| 음성 인식 (STT) | Faster-Whisper `small` 모델, `int8` CPU 추론, VAD 필터 |
| 화자 분리 | WhisperX + pyannote.audio (`HF_TOKEN` 필요) |
| AI 요약 | Gemini API, 10개 회의 유형별 프롬프트, 참고파일 첨부 지원 |
| 실시간 진행 | SSE(Server-Sent Events) 이중 게이지 — 전체 / 단계별 진행률 |
| 결과 다운로드 | AI 요약(MD) / 화자별 스크립트(TXT) / 전체 원문(TXT) 저장 |

### 실행 방법

```powershell
cd audio_extractor_stt

# 최초 실행 시 의존성 설치
uv sync

# 터미널 1 — FastAPI 백엔드 (포트 8000)
uv run uvicorn main:app --reload --port 8000

# 터미널 2 — React 프론트엔드 (포트 5173, 핫 리로드)
cd frontend
npm install   # 최초 1회
npm run dev   # → http://localhost:5173
```

**프로덕션 빌드 (단일 서버)**

```powershell
cd frontend ; npm run build   # frontend/dist/ 생성
cd ..
uv run uvicorn main:app --port 8000   # 정적 파일 + SPA fallback 서빙
```

**CLI (배치 처리)**

```powershell
uv run python run_cli.py "videos/회의.mp4"
# 결과: results/<파일명>_<YYYYmmdd_HHMMSS>.md
```

### 요구 사항

| 항목 | 내용 |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ (프론트엔드 빌드 시) |
| FFmpeg | PATH에 등록 필요 |
| `.env` 파일 | `audio_extractor_stt/.env` — 아래 변수 설정 |

```dotenv
MINUTE_SECOND_API_KEY=your_gemini_api_key
HF_TOKEN=your_huggingface_token   # 화자 분리 모델 (선택)
```

> `HF_TOKEN` 미설정 시 화자 분리를 건너뛰고 전체 텍스트만 출력합니다.

### 프로젝트 구조

```
audio_extractor_stt/
  main.py               FastAPI 앱 — 잡 관리, SSE, 정적 파일 서빙
  audio_extractor.py    FFmpeg 오디오 추출 (sync + async 컨텍스트 매니저)
  stt_processor.py      Faster-Whisper STT + WhisperX 화자 분리
  summarizer.py         Gemini API 요약 (10개 회의 유형 프롬프트)
  run_cli.py            CLI 파이프라인 (배치 처리, 터미널 게이지)
  pyproject.toml        uv 패키지 관리 (torch CPU 전용)
  frontend/
    src/
      App.tsx           React 상태 머신 (idle→uploading→processing→done|error)
      api.ts            createJob / subscribeJobEvents / fetchJobResult
      components/
        UploadZone.tsx  드롭존 + 회의유형 선택 + 참고파일 첨부
        ProgressLog.tsx SSE 로그 + 이중 게이지 UI
        ResultTabs.tsx  3탭 결과 (요약 / 화자별 / 원문) + 복사 / 다운로드

teams-caption-saver/
  manifest.json         MV3 — sidePanel 권한, host_permissions
  content_script.js     자막 감지 (MutationObserver) + 참석자 추적
  service_worker.js     저장, 배지 업데이트, 세션 히스토리
  popup.html            4탭 팝업 UI (Catppuccin dark 테마)
  sidepanel.html        Chrome Side Panel 전용 와이드 레이아웃
  popup.js              팝업 / 사이드바 공통 스크립트
  viewer.html           3탭 자막 뷰어 (AI 요약 + 참고파일)
  viewer.js             뷰어 로직 (Gemini / OpenAI API 호출)
  pdf.min.js            PDF.js 3.11.174 (참고파일 PDF 파싱)
```

---

## 상세 문서

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 전체 시스템 아키텍처 및 데이터 흐름 |
| [docs/audio-extractor-stt.md](docs/audio-extractor-stt.md) | FastAPI + React 서비스 상세 설계 |
| [docs/teams-caption-saver.md](docs/teams-caption-saver.md) | Chrome 확장 상세 설계 |
| [docs/development-guide.md](docs/development-guide.md) | 개발 환경 설정 및 실행 가이드 |

