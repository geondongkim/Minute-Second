# Minute Second — 시스템 아키텍처

> 작성: 2026-04-27 | 기준: `audio_extractor_stt/` + `teams-caption-saver/` + `lecture-slide-notes/`
>
> **범위**: 독립 서비스와 로컬 도구의 전체 데이터 흐름, 컴포넌트 역할, 통신 프로토콜

---

## 1. 서비스 개요

```
Minute Second 모노레포
│
├── audio_extractor_stt/       동영상 → STT → 회의록 웹 서비스
│     └── FastAPI + React + Faster-Whisper + Gemini
│
├── teams-caption-saver/       Teams 자막 실시간 캡처 + AI 요약
│     └── Chrome Extension MV3 (팝업 + 사이드바 + 뷰어)
│
└── lecture-slide-notes/       Vimeo/YouTube/로컬 강의 영상 → 슬라이드 노트
      └── CLI + yt-dlp + FFmpeg + OCR + Gemini + MCP 확장 골격
```

각 도구는 **공유 인프라 없이 독립 실행**되며, 공통 개념(동영상 입력, Gemini 기반 후처리, Markdown 결과 포맷)만 공유합니다.

### 1-1. lecture-slide-notes — 전체 데이터 흐름

```
강의 페이지 URL / Vimeo player URL / YouTube URL / 로컬 동영상
       │
       ▼
SourceResolver
       │     └─ Vimeo iframe, YouTube iframe, referer, direct manifest 후보 정리
       ▼
DownloadManager (yt-dlp)
       │     └─ Vimeo player URL 또는 YouTube watch URL + optional referer/cookies
       ▼
FFmpeg frame sampling
       │
       ▼
Stable slide detector
       │     └─ transition frame 제거, min-gap, dedupe, contact sheet
       ▼
slides/ + slides_pdf/
       │
       ├─ OCR adapter → slide별 원문 텍스트
       ├─ optional Gemini correction → NotebookLM용 구조화 보정
       ├─ Markdown builder → *_notes.md
       └─ PDF builder → searchable PDF
```

---

## 2. audio_extractor_stt — 전체 데이터 흐름

```
브라우저 (React SPA)
       │
       │  1. POST /api/jobs (multipart/form-data)
       │     └─ file (동영상), meeting_type, ref_text
       ▼
FastAPI 백엔드 (main.py) ── asyncio 이벤트 루프
       │
       │  2. 비동기 처리 태스크 시작 (asyncio.create_task)
       │     └─ in-memory job store: { job_id → status, queue, logs, result }
       │
       ├── 3. GET /api/jobs/{id}/events (SSE 구독)
       │     └─ EventSourceResponse → 실시간 로그 스트림
       │
       │  ── 처리 파이프라인 (asyncio.to_thread — CPU-bound 논블로킹) ──
       │
       ├─ [Stage 1]  FFmpeg 오디오 추출
       │     └─ video → 16kHz / 모노 WAV (임시 파일)
       │
       ├─ [Stage 2]  Faster-Whisper STT
       │     └─ WAV → 세그먼트 목록 (start/end/text)
       │     └─ VAD 필터 (min_silence_duration_ms=500)
       │     └─ language="ko", beam_size=1, int8
       │
       ├─ [Stage 3]  WhisperX 정렬 + 화자 분리
       │     └─ load_align_model → 단어 수준 정렬
       │     └─ pyannote.audio DiarizationPipeline
       │     └─ HF_TOKEN 없으면 graceful degradation (화자 분리 생략)
       │
       ├─ [Stage 4]  Gemini API 요약
       │     └─ meeting_type 별 프롬프트 선택 (10종)
       │     └─ ref_text 있으면 [참고자료] 블록 추가
       │     └─ 3섹션 출력: 주요안건 / 핵심논의 / Action Item
       │
       └─ 4. GET /api/jobs/{id}/result (JSON 결과 조회)
             └─ { summary, speaker_text, combined_text }
```

### 2-1. API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/jobs` | 동영상 업로드 + 처리 시작 → `{ job_id }` 반환 |
| `GET` | `/api/jobs/{id}/events` | SSE 스트림 — 실시간 로그 + 진행률 |
| `GET` | `/api/jobs/{id}/result` | 처리 결과 JSON 조회 |

### 2-2. SSE 메시지 프로토콜

| 메시지 패턴 | 의미 |
|---|---|
| 평문 텍스트 | 사람이 읽는 로그 (화면 출력용) |
| `__PROGRESS__:{json}` | 진행률 업데이트 — `overall`, `stage_label`, `stage_pct`, `elapsed_s`, `eta_s` |
| `__DONE__` | 처리 완료 센티넬 |
| `__ERROR__:{message}` | 처리 실패 센티넬 |

### 2-3. 진행률 매핑

| 전체(overall) 범위 | 단계 |
|---|---|
| 1 → 5% | FFmpeg 오디오 추출 |
| 5 → 52% | Faster-Whisper STT |
| 52 → 68% | WhisperX 정렬 |
| 70 → 93% | pyannote 화자 분리 |
| 95 → 100% | Gemini 요약 |

---

## 3. audio_extractor_stt — 컴포넌트 구조

```
audio_extractor_stt/
│
├── main.py
│     FastAPI 앱, 잡 라이프사이클 관리 (생성/SSE/조회)
│     asyncio.create_task → _process_job() 비동기 실행
│     aiofiles 스트리밍 청크 업로드 (1 MB 단위)
│
├── audio_extractor.py
│     extract_audio_from_video()     — 동기 컨텍스트 매니저
│     async_extract_audio_from_video() — 비동기 컨텍스트 매니저
│     내부: asyncio.to_thread(ffmpeg.run)
│
├── stt_processor.py
│     process_audio(audio_path, progress_cb, diarize) → (combined_text, speaker_text)
│     모델 싱글톤: threading.Lock + double-checked locking
│       _whisper_model  (Faster-Whisper)
│       _diarize_model  (pyannote DiarizationPipeline)
│       _align_models   (WhisperX, 언어별 캐시)
│     _build_speech_only_audio() — 묵음 제거 후 화자분리 정확도 향상
│     _DiarizeTimer — pyannote 진행률 추정 스레드 (2초 인터벌)
│
├── summarizer.py
│     summarize_text(text, meeting_type, ref_text) → str
│     _MEETING_PROMPTS  : 10개 회의유형 프롬프트 dict
│     _OUTPUT_STRUCTURE : 3섹션 Markdown 포맷 명세
│     google.genai.Client → gemini-3.1-flash-lite-preview
│
├── run_cli.py
│     argparse CLI — 단일 파일 또는 배치 처리
│     터미널 게이지 [████░░] + ETA 표시
│     결과: results/<이름>_<timestamp>.md
│
└── frontend/
      src/
        App.tsx           상태 머신 (5-phase)
        api.ts            HTTP/SSE 클라이언트
        components/
          UploadZone.tsx  드롭존 + 설정 패널
          ProgressLog.tsx 이중 게이지 + 로그
          ResultTabs.tsx  3탭 결과 + 복사/다운로드
```

---

## 4. teams-caption-saver — 전체 데이터 흐름

```
Microsoft Teams 탭
       │
       │  MutationObserver — 자막 DOM 변화 감지
       ▼
content_script.js
 ├─ 자막 텍스트 추출 + 발화자 파싱
 ├─ 발화 완료 감지 (텍스트 안정화 + 딜레이)
 ├─ 참석자 목록 추적
 └─ chrome.runtime.sendMessage → service_worker.js

       │  { type: 'NEW_CAPTION', speaker, text, timestamp }
       ▼
service_worker.js
 ├─ chrome.storage.local — 자막 세션 누적 저장
 ├─ 5분 주기 자동 저장 (chrome.alarms)
 ├─ chrome.downloads.download() — 포맷별 내보내기
 ├─ 배지 업데이트 (캡처 문장 수 표시)
 └─ 세션 히스토리 관리 (최근 10회)

       │  chrome.storage.local / chrome.tabs.sendMessage
       ▼
popup.html + sidepanel.html  (공통: popup.js)
 ├─ 캡처 탭: 상태 표시, 즉시 저장, 뷰어 열기
 ├─ 설정 탭: chrome.storage.sync 저장
 ├─ AI 요약 탭: API 키/모델 설정
 └─ 히스토리 탭: 세션 목록

       │  chrome.tabs.create → viewer.html?session=...
       ▼
viewer.html + viewer.js
 ├─ 📄 원문 탭: 발화자 필터 + 검색 + LIVE 업데이트
 ├─ 🗣️ 발화자별 탭: 그룹화 목록
 └─ 📌 AI 요약 탭
       ├─ 회의유형 선택 (10종)
       ├─ 참고파일 첨부 (MD / TXT / PDF.js 파싱)
       └─ Gemini / OpenAI API 직접 호출 → 3섹션 결과
```

### 4-1. 파일 역할

| 파일 | 역할 |
|---|---|
| `manifest.json` | MV3 선언 — sidePanel 권한, host_permissions, CSP |
| `content_script.js` | Teams DOM 감지, 자막/참석자 추출, service_worker 통신 |
| `service_worker.js` | 자막 저장, 자동저장 알람, 다운로드, 히스토리 |
| `popup.html` | 4탭 팝업 UI (340px 고정, Catppuccin dark 테마) |
| `sidepanel.html` | Chrome Side Panel 전용 와이드 레이아웃 (`popup.js` 공유) |
| `popup.js` | 팝업 / 사이드바 공통 로직 (탭 전환, 상태 반영, AI 설정) |
| `viewer.html` | 3탭 자막 뷰어 (팝업과 별도 탭으로 열림) |
| `viewer.js` | 뷰어 로직 (Gemini / OpenAI 직접 호출, PDF.js 연동) |
| `pdf.min.js` | PDF.js 3.11.174 번들 (참고파일 PDF 텍스트 추출) |

### 4-2. Chrome 권한 구조

| 권한 | 용도 |
|---|---|
| `downloads` | 자막 파일 로컬 저장 |
| `storage` | 자막 세션, 설정, 히스토리 저장 (`sync` / `local`) |
| `tabs` | 현재 Teams 탭 식별, 뷰어 탭 생성 |
| `sidePanel` | Chrome Side Panel API (Chrome 114+) |
| `https://teams.microsoft.com/*` 外 | content_script 주입 대상 |
| `https://generativelanguage.googleapis.com/*` | Gemini API 직접 호출 |
| `https://api.openai.com/*` | OpenAI API 직접 호출 |

---

## 5. 핵심 엔지니어링 결정

### 5-1. CPU 전용 STT — 모델 선택 근거

```
모델 크기 비교 (한국어 기준)
  tiny   → 정확도 불충분 (한국어 인식률 낮음)
  small  → 채택: 속도 / 정확도 균형 최적점
  medium → 2× 느림 대비 정확도 개선 미미
  large  → 로컬 CPU에서 실사용 불가 (너무 느림)

추론 설정:
  compute_type="int8"         → 메모리 / 속도 최적화
  beam_size=1, best_of=1      → 탐색 최소화 (속도 우선)
  vad_filter=True             → 묵음 구간 스킵으로 처리량 감소
  condition_on_previous_text=False → 세그먼트 독립 처리 (오류 전파 차단)
```

### 5-2. 동시성 설계 — asyncio + threading 혼용

```
FastAPI (asyncio 이벤트 루프)
       │
       ├─ await file.read()          → 비동기 I/O (이벤트 루프 내)
       ├─ await asyncio.to_thread()  → CPU-bound 작업을 스레드풀에 위임
       │    └─ FFmpeg, Faster-Whisper, pyannote, Gemini API
       │
       ├─ asyncio.Queue             → 스레드 → 이벤트 루프 안전 메시지 전달
       │    └─ loop.call_soon_threadsafe(queue.put_nowait, msg)
       │
       └─ EventSourceResponse       → SSE 스트림 (큐 구독)
```

### 5-3. 모델 싱글톤 — double-checked locking

```python
# 스레드풀에서 동시에 process_audio() 호출 시 모델 중복 로딩 방지
if _whisper_model is None:          # 1차 확인 (락 없이)
    with _lock:
        if _whisper_model is None:  # 2차 확인 (락 보유 상태)
            _whisper_model = WhisperModel(...)
```

**효과:** 최초 1회만 모델 로딩 (수십 초) → 이후 재사용 (~0초)

### 5-4. Chrome Side Panel — popup.js 공유 전략

```
popup.html   ── <script src="popup.js">  ─┐
sidepanel.html ── <script src="popup.js"> ─┤ 동일 스크립트
                                           └→ 모든 ID 동일 유지
                                              팝업: width=340px 고정
                                              사이드바: width=100% 유동
```

**chrome.sidePanel.open() 호출 시:**
1. 팝업에서 "사이드바" 버튼 클릭
2. `chrome.tabs.query()` → `windowId` 획득
3. `chrome.sidePanel.open({ windowId })` → 브라우저 우측에 sidepanel.html 로드
4. `window.close()` → 팝업 자동 닫힘

---

## 6. 공통 설계 패턴 — 회의 유형별 AI 요약

회의록/캡션 계열 서비스는 동일한 10개 회의 유형과 3섹션 출력 구조를 사용합니다.

### 6-1. 회의 유형 (10종)

| 키 | 한국어명 | 핵심 출력 항목 |
|---|---|---|
| `general` | 일반 회의 | 결정사항, 핵심 논의, 액션아이템 |
| `standup` | 스탠드업 / 데일리 | 어제/오늘/블로커 표 |
| `retro` | 회고 | Keep / Problem / Try |
| `planning` | 플래닝 | 스프린트 목표, 작업 목록, 예상 이슈 |
| `executive` | 경영진 회의 | 결정사항, 주요 지표, 후속 조치 |
| `interview` | 인터뷰 | 주요 답변, 강점, 우려사항, 평가 |
| `brainstorm` | 브레인스토밍 | 카테고리별 아이디어, 우선순위 |
| `review` | 리뷰 (코드/디자인) | 검토 내용, 수정 요청, 후속 조치 |
| `1on1` | 1:1 미팅 | 업무, 성장 계획, 피드백, 액션아이템 |
| `lecture` | 라이브 강의 | 주제, 핵심 개념, 예시, Q&A, 학습 포인트 |

### 6-2. 출력 구조 (3섹션 Markdown)

```markdown
## 📌 주요 안건
(회의에서 다룬 핵심 주제 목록)

## 🗣️ 핵심 논의 내용
(회의 유형별 맞춤 상세 내용)

## ✅ Action Item (담당자 및 기한)
(후속 조치 + 담당자 + 기한)
```
