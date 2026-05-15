# 개발 환경 설정 및 실행 가이드

> 작성: 2026-04-27 | 기준: `audio_extractor_stt/pyproject.toml`, `audio_extractor_stt/frontend/`, `script-saver/manifest.json`, `lecture-slide-notes/pyproject.toml`
>
> **범위**: 로컬 개발 환경 구성, 서비스 실행, CLI 사용, 프로덕션 빌드, 확장 로드

---

## 1. 사전 요구 사항

| 도구 | 버전 | 확인 명령어 |
|---|---|---|
| Python | 3.10+ | `python --version` |
| [uv](https://docs.astral.sh/uv/) | 최신 | `uv --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| FFmpeg | 임의 | `ffmpeg -version` |
| Tesseract OCR | 선택 | `tesseract --version` |
| Chrome | 114+ | 브라우저 버전 확인 (사이드 패널용) |

**FFmpeg 설치 (Windows):**
```powershell
# winget
winget install Gyan.FFmpeg

# 또는 chocolatey
choco install ffmpeg
```

**uv 설치:**
```powershell
# PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

---

## 2. 저장소 클론

```powershell
git clone --recurse-submodules https://github.com/geondongkim/Minute-Second.git
cd Minute-Second

# 이미 clone한 경우
git submodule update --init --recursive
```

---

## 3. lecture-slide-notes — 강의 슬라이드 노트 CLI

### 3-1. 의존성 설치

```powershell
cd lecture-slide-notes
uv sync --extra ocr --extra mcp
```

### 3-2. 환경 점검

```powershell
uv run lecture-slide-notes doctor
```

### 3-3. 로컬 동영상 처리

```powershell
uv run lecture-slide-notes process-video ..\videos\lecture.mp4 --output ..\outputs\lecture
```

### 3-4. Vimeo/YouTube URL 처리

```powershell
uv run lecture-slide-notes process-url "https://player.vimeo.com/video/<id>" --referer "https://academy.example/lesson" --output-root ..\outputs

uv run lecture-slide-notes process-url "https://www.youtube.com/watch?v=<id>" --output-root ..\outputs
```

로그인 강의 사이트와 일부 YouTube 계정 제한 영상은 비밀번호를 저장하지 않고 `--cookies-from-browser chrome` 또는 `--cookies-from-browser edge`를 사용합니다.

---

## 4. audio_extractor_stt — 백엔드 설정

### 4-1. 의존성 설치

```powershell
cd audio_extractor_stt
uv sync
```

`uv sync`는 `pyproject.toml`을 읽어 가상환경(`.venv`)을 생성하고 모든 패키지를 설치합니다. PyTorch CPU 빌드는 별도 PyTorch 인덱스에서 자동으로 다운로드됩니다.

> **소요 시간:** 첫 실행 시 약 5~15분 (PyTorch, faster-whisper 등 대용량 패키지)

### 4-2. 환경 변수 설정

`audio_extractor_stt/.env` 파일 생성:

```dotenv
# Gemini API 키 (필수)
# https://aistudio.google.com/app/apikey 에서 발급
MINUTE_SECOND_API_KEY=AIza...

# Hugging Face 토큰 (선택 — 화자 분리 활성화)
# https://huggingface.co/settings/tokens 에서 발급
# pyannote/speaker-diarization-3.1 모델 이용 약관 수락 필요
# https://huggingface.co/pyannote/speaker-diarization-3.1
HF_TOKEN=hf_...
```

> **HF_TOKEN 없이 실행 시:** STT는 정상 동작, 화자 분리 건너뜀 (화자별 스크립트 = 전체 원문)

---

## 5. audio_extractor_stt — 개발 서버 실행

### 5-1. 백엔드 (FastAPI)

```powershell
# audio_extractor_stt/ 디렉터리에서
uv run uvicorn main:app --reload --port 8000
```

| 옵션 | 설명 |
|---|---|
| `--reload` | 파일 변경 시 자동 재시작 (개발용) |
| `--port 8000` | 포트 번호 |

API 문서: `http://localhost:8000/docs` (Swagger UI 자동 생성)

### 5-2. 프론트엔드 (React + Vite)

```powershell
# audio_extractor_stt/frontend/ 디렉터리에서
npm install      # 최초 1회
npm run dev      # → http://localhost:5173
```

**Vite 개발 서버 특징:**
- 핫 리로드 (HMR) — 코드 변경 즉시 반영
- `/api/*` 요청은 `vite.config.ts`의 proxy 설정으로 `:8000`에 전달 (CORS 없음)

> 백엔드(8000)와 프론트엔드(5173) 둘 다 실행 필요. 브라우저에서는 `:5173`으로 접속.

---

## 6. audio_extractor_stt — 프로덕션 빌드

단일 서버로 React SPA + FastAPI를 함께 서빙합니다.

```powershell
# 1. 프론트엔드 빌드
cd audio_extractor_stt/frontend
npm run build
# → audio_extractor_stt/frontend/dist/ 에 정적 파일 생성

# 2. FastAPI 서버 실행 (정적 파일 포함)
cd ..
uv run uvicorn main:app --port 8000
```

`main.py`가 `frontend/dist/`를 `StaticFiles`로 마운트하고 SPA fallback을 처리하므로, `:8000` 하나만 열면 됩니다.

---

## 7. audio_extractor_stt — CLI 사용법 (`run_cli.py`)

서버 없이 터미널에서 직접 동영상을 처리할 때 사용합니다.

### 7-1. 기본 사용법

```powershell
cd audio_extractor_stt

# 단일 파일 처리
uv run python run_cli.py "videos/회의.mp4"

# 출력 디렉터리 지정
uv run python run_cli.py "videos/회의.mp4" --output-dir "output/"
```

### 7-2. 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `video_file` | (필수) | 처리할 동영상 파일 경로 |
| `--output-dir` | `results/` | 결과 Markdown 저장 디렉터리 |
| `--meeting-type` | `general` | 회의 유형 키 (10종) |

### 7-3. 출력 형식

```
results/
  회의_20260427_143022.md
```

**파일 내용 구조:**
```markdown
# 회의록 — 회의 (2026-04-27 14:30)

## 📌 주요 안건
...

## 🗣️ 핵심 논의 내용
...

## ✅ Action Item (담당자 및 기한)
...

---
## 🗣️ 화자별 스크립트
SPEAKER_00:
  안녕하세요...

---
## 📄 전체 원문
[00:00:01] 안녕하세요...
```

### 7-4. 터미널 게이지 표시

```
[████████████░░░░░░░░░░░░░░░░░░] 40%  화자 분리 중 (60%)  ETA 2분 30초
```

---

## 8. script-saver — Chrome 확장 로드

### 8-1. 개발 모드 로드

1. Chrome에서 `chrome://extensions/` 열기
2. 우상단 **"개발자 모드"** 토글 활성화
3. **"압축 해제된 확장 프로그램 로드"** 클릭
4. `Minute_Second/script-saver/` 폴더 선택

> 코드 변경 후 `chrome://extensions/`에서 새로고침 버튼(↺) 클릭 필요

### 8-2. 사이드바 열기 테스트

1. `teams.microsoft.com` 또는 Teams 회의 탭 활성화
2. 확장 팝업 열기 → 우상단 "↗ 사이드바" 버튼 클릭
3. 브라우저 우측에 사이드바 패널이 열리면 정상

> Chrome 113 이하에서는 `chrome.sidePanel` API 미지원으로 콘솔에 오류 출력

### 8-3. AI 요약 설정

1. 팝업 또는 사이드바 → **AI 요약 탭**
2. AI 제공자 선택 (Gemini / OpenAI)
3. API 키 입력 후 저장
4. 뷰어에서 **📌 AI 요약** 탭 → 회의 유형 선택 → "AI 요약 생성" 클릭

---

## 9. 프로젝트 구조 전체

```
Minute_Second/
│
├── README.md
├── .env                          (루트 레벨, 미사용)
├── .gitignore
│
├── docs/                         문서
│     ├── architecture.md         전체 시스템 아키텍처
│     ├── audio-extractor-stt.md  웹 서비스 상세 설계
│     ├── script-saver.md         Chrome 확장 상세 설계
│     ├── lecture-slide-notes.md  강의 슬라이드 노트 생성기 설계
│     └── development-guide.md    개발 환경 설정 (이 문서)
│
├── lecture-slide-notes/          Vimeo/YouTube/로컬 강의 영상 → 슬라이드 PDF + Markdown
│     ├── pyproject.toml          uv 패키지 관리
│     ├── README.md               CLI/MCP 사용법
│     ├── src/lecture_slide_notes/
│     │     ├── cli.py            CLI 진입점
│     │     ├── sources.py        Vimeo/YouTube/course/local source resolver
│     │     ├── downloader.py     yt-dlp 다운로드/metadata 추출
│     │     ├── slides.py         FFmpeg sampling + stable slide detection
│     │     ├── ocr.py            OCR adapter
│     │     ├── markdown.py       NotebookLM Markdown 생성
│     │     ├── pdf.py            searchable PDF 생성
│     │     └── mcp_server.py     MCP 서버 골격
│     └── tests/
│
├── audio_extractor_stt/          FastAPI + React 웹 서비스
│     ├── .env                    환경 변수 (MINUTE_SECOND_API_KEY, HF_TOKEN)
│     ├── main.py                 FastAPI 앱
│     ├── audio_extractor.py      FFmpeg 오디오 추출
│     ├── stt_processor.py        Faster-Whisper + pyannote STT
│     ├── summarizer.py           Gemini AI 요약
│     ├── run_cli.py              CLI 파이프라인
│     ├── pyproject.toml          uv 패키지 관리
│     ├── uv.lock                 의존성 잠금 파일
│     ├── frontend/               React 19 + Vite + TypeScript
│     │     ├── src/
│     │     │     ├── App.tsx
│     │     │     ├── api.ts
│     │     │     └── components/
│     │     └── package.json
│     ├── videos/                 동영상 파일 (gitignore)
│     └── results/                CLI 출력 결과 (gitignore)
│
├── script-saver/                 Chrome Extension MV3
│     ├── manifest.json
│     ├── content_script.js
│     ├── service_worker.js
│     ├── popup.html / popup.js
│     ├── sidepanel.html
│     ├── viewer.html / viewer.js
│     └── pdf.min.js / pdf.worker.min.js
│
└── ref/                          참고 문서 (ACV 프로젝트)
      ├── 프로젝트 제안서(ACV).md
      ├── 아키텍처(ACV).md
      └── 데이터 구조 전체(ACV).md
```

---

## 10. 자주 발생하는 문제

### Q1. `uv sync` 중 `torchcodec` 설치 오류 (Windows)

```
error: Distribution `torchcodec` can't be installed because it doesn't have a source distribution or wheel for the current platform
```

**원인:** pyannote-audio 4.x가 torchcodec을 의존하지만 Windows DLL 미지원  
**해결:** `pyproject.toml`의 `override-dependencies`로 이미 처리됨. `uv sync`를 재실행하거나 uv 버전을 최신으로 업데이트.

---

### Q2. 화자 분리 모델 로딩 실패 (`Access to model pyannote/...`)

```
OSError: Access to model pyannote/speaker-diarization-3.1 is restricted.
```

**원인:** Hugging Face 모델 이용 약관 미수락  
**해결:**
1. [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) 방문 → 이용 약관 수락
2. [HF Settings](https://huggingface.co/settings/tokens) 에서 액세스 토큰 발급
3. `.env`에 `HF_TOKEN=hf_...` 추가

---

### Q3. FFmpeg 찾을 수 없음

```
FileNotFoundError: [WinError 2] The system cannot find the file specified
```

**원인:** FFmpeg이 PATH에 없음  
**해결:** `winget install Gyan.FFmpeg` 실행 후 터미널 재시작

---

### Q4. Chrome 확장에서 "사이드바" 버튼이 오류 없이 동작하지 않음

**원인:** Chrome 버전이 114 미만  
**해결:** Chrome 업데이트 (`chrome://settings/help`)

---

### Q5. Gemini 요약 시 `MINUTE_SECOND_API_KEY` 오류

```
Error: MINUTE_SECOND_API_KEY environment variable not set.
```

**원인:** `.env` 파일 미생성 또는 변수명 오류  
**해결:** `audio_extractor_stt/.env`에 `MINUTE_SECOND_API_KEY=AIza...` 추가
