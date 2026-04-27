# audio_extractor_stt — 서비스 상세 설계

> 작성: 2026-04-27 | 버전: v0.2.0 | 기준: `pyproject.toml`, `main.py`, `stt_processor.py`, `summarizer.py`
>
> **범위**: FastAPI 백엔드 + React 프론트엔드 전체 설계, 파이프라인 각 단계 상세, 환경 설정

---

## 1. 서비스 개요

동영상 파일을 업로드하면 서버 측에서 오디오 추출 → STT → 화자 분리 → AI 요약 순으로 처리하고, 브라우저에 실시간 진행 상태를 SSE로 전달하여 최종 회의록 3종을 반환합니다.

**처리 결과 3종:**

| 탭 | 내용 | 저장 포맷 |
|---|---|---|
| 📌 AI 회의록 요약 | Gemini 생성 3섹션 Markdown | `.md` |
| 🗣️ 화자별 스크립트 | 발화자별 그룹화 대화 목록 | `.txt` |
| 📄 전체 원문 | STT 전체 텍스트 (시간순) | `.txt` |

---

## 2. 백엔드 — FastAPI (`main.py`)

### 2-1. 엔드포인트 명세

#### `POST /api/jobs`

동영상 파일 업로드 및 처리 시작.

**요청 (multipart/form-data):**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `file` | binary | ✅ | 동영상 파일 (MP4 / MKV / AVI / MOV) |
| `meeting_type` | string | — | 회의 유형 키 (기본값: `general`) |
| `ref_text` | string | — | 참고자료 텍스트 (기본값: 빈 문자열) |

**응답 (200 OK):**
```json
{ "job_id": "550e8400-e29b-41d4-a716-446655440000" }
```

**오류:**
- `500` — 파일 저장 실패 (디스크 I/O 오류)

---

#### `GET /api/jobs/{job_id}/events`

SSE(Server-Sent Events) 스트림으로 실시간 진행 상태를 수신합니다.

**메시지 형식:**

```
data: STT 변환 중 (Faster-Whisper)...\n\n
data: __PROGRESS__:{"overall":25,"stage_label":"음성 텍스트 변환 중","stage_pct":40,"elapsed_s":12,"eta_s":30}\n\n
data: __DONE__\n\n
```

| 메시지 패턴 | 처리 방법 |
|---|---|
| 평문 | UI 로그 패널에 출력 |
| `__PROGRESS__:{json}` | 게이지 업데이트 (`overall`, `stage_label`, `stage_pct`, `elapsed_s`, `eta_s`) |
| `__DONE__` | SSE 종료 → 결과 조회 API 호출 |
| `__ERROR__:{msg}` | SSE 종료 → 오류 메시지 표시 |

**재연결 지원:** 연결 끊김 후 재연결 시 기존 로그(`job["logs"]`)를 모두 재전송한 후 큐 구독 재개.

---

#### `GET /api/jobs/{job_id}/result`

처리 완료된 결과를 JSON으로 반환합니다.

**응답 (200 OK):**
```json
{
  "summary":       "## 📌 주요 안건\n...",
  "speaker_text":  "SPEAKER_00:\n  안녕하세요...\nSPEAKER_01:\n  반갑습니다...",
  "combined_text": "[00:00:01] 안녕하세요 [00:00:03] 반갑습니다..."
}
```

**오류:**
- `404` — 해당 `job_id` 없음

---

### 2-2. 잡 라이프사이클

```
POST /api/jobs
       │
       ▼  tempfile.mkstemp() → aiofiles 1 MB 청크 스트리밍 저장
       │
       ▼  asyncio.create_task(_process_job(...))
       │
       ├─ status: "processing"
       │     └─ asyncio.Queue: 로그 메시지 스트림
       │
       ├─ status: "done"
       │     └─ result: { summary, speaker_text, combined_text }
       │
       └─ status: "error"
             └─ error: str
```

**잡 저장소:** `_jobs: dict[str, dict]` — in-memory, 단일 사용자 전제, 서버 재시작 시 초기화

---

## 3. 처리 파이프라인 상세

### 3-1. Stage 1 — FFmpeg 오디오 추출 (`audio_extractor.py`)

```python
async_extract_audio_from_video(video_path)
  └─ asyncio.to_thread(ffmpeg.run)
       └─ ffmpeg -i input -ac 1 -ar 16000 -f wav output.wav
```

| 설정 | 값 | 이유 |
|---|---|---|
| 채널 | 1 (모노) | STT 모델 입력 요구사항 |
| 샘플레이트 | 16,000 Hz | Whisper 최적 입력 포맷 |
| 포맷 | WAV | 손실 없는 중간 포맷 |
| 임시 파일 | `tempfile.mkstemp()` | 처리 완료 후 자동 삭제 |

---

### 3-2. Stage 2 — Faster-Whisper STT (`stt_processor.py`)

```python
WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=os.cpu_count())

model.transcribe(
    audio_path,
    language="ko",
    beam_size=1,
    best_of=1,
    temperature=0,
    condition_on_previous_text=False,
    word_timestamps=False,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
)
```

**설계 근거:**

| 파라미터 | 설정 | 이유 |
|---|---|---|
| `model` | `small` | CPU 환경에서 속도/정확도 최적점 |
| `compute_type` | `int8` | 메모리 사용량 1/4 수준, 속도 향상 |
| `cpu_threads` | `os.cpu_count()` | 논리 코어 전부 활용 |
| `beam_size=1` | 1 | 탐색 최소화 (속도 우선) |
| `temperature=0` | 0 | 확정적 출력 (재현성 확보) |
| `condition_on_previous_text` | `False` | 세그먼트 독립 처리 (오류 전파 차단) |
| `vad_filter` | `True` | 묵음 구간 스킵 → 처리량 대폭 감소 |

**진행률 매핑:** `5% + (segment.end / info.duration × 47%)` → 전체 5%→52% 범위

---

### 3-3. Stage 3 — WhisperX 화자 분리

**화자 분리 흐름:**

```
transcribed_segments (Faster-Whisper 결과)
       │
       ▼  _build_speech_only_audio()
            묵음 제거 → speech-only 오디오 생성 (pyannote 입력용)
            패딩: 100ms (음절 경계 보호)
       │
       ▼  whisperx.load_align_model(language_code, device="cpu")
            음소 수준 타임스탬프 정렬
       │
       ▼  whisperx.align(segments, align_model, metadata, audio)
       │
       ▼  DiarizationPipeline(token=HF_TOKEN, device="cpu")
            pyannote.audio — 화자 구분
       │
       ▼  whisperx.assign_word_speakers(diarize_segments, result)
            세그먼트별 SPEAKER_00, SPEAKER_01 ... 태깅
```

**graceful degradation:** `HF_TOKEN` 미설정 또는 pyannote 로딩 실패 시 `_LOAD_FAILED` 센티넬을 반환하고 화자 분리 없이 전체 텍스트만 출력합니다.

**_DiarizeTimer:** pyannote는 내부 진행률 콜백이 없으므로, 백그라운드 스레드가 2초마다 `speech_duration × 3.0`으로 ETA를 추정하여 SSE로 전파합니다.

---

### 3-4. Stage 4 — Gemini AI 요약 (`summarizer.py`)

#### 프롬프트 구성 (최종 전달 구조)

```
{base_instruction}          ← meeting_type별 지시문
{_OUTPUT_STRUCTURE}         ← 3섹션 포맷 명세
                            ← (ref_text 있을 때만)
[참고자료]
────────────────────────────
{ref_text}
────────────────────────────

[전체 텍스트]
────────────────────────────
{combined_text}
────────────────────────────
```

#### API 호출 설정

| 항목 | 값 |
|---|---|
| 라이브러리 | `google-genai` (`google.genai.Client`) |
| 모델 | `gemini-3.1-flash-lite-preview` |
| 환경변수 | `MINUTE_SECOND_API_KEY` |
| 오류 처리 | 예외 발생 시 오류 메시지 문자열 반환 (서비스 중단 없음) |

---

## 4. 프론트엔드 — React 19 (`frontend/`)

### 4-1. 상태 머신 (`App.tsx`)

```
idle
  │  파일 선택 + 분석 시작 버튼 클릭
  ▼
uploading  { progress: 0-100 }
  │  XHR upload complete → job_id 수신
  ▼
processing  { jobId, logs: string[], progress: ProgressEvent | null }
  │  SSE __DONE__ 수신 → fetchJobResult()
  ▼
done  { result: JobResult }
  │  "새 파일 분석" 버튼 클릭
  ▼
idle

  ※ 어느 단계에서든 오류 발생 시
  → error  { message: string }  → idle 복귀 가능
```

### 4-2. API 클라이언트 (`api.ts`)

| 함수 | 역할 |
|---|---|
| `createJob(file, onProgress, meetingType, refText)` | XHR multipart 업로드 (XMLHttpRequest — fetch 불가) |
| `subscribeJobEvents(jobId, onLog, onDone, onError, onProgress)` | EventSource SSE 구독 + 메시지 라우팅 |
| `fetchJobResult(jobId)` | GET 결과 JSON 조회 |

**XHR 사용 이유:** Fetch API는 `upload.progress` 이벤트를 지원하지 않아 업로드 진행률 표시 불가.

### 4-3. 컴포넌트 (`components/`)

#### `UploadZone.tsx`

```
upload-zone-wrapper
  ├── upload-zone          (드래그&드롭 영역)
  │     ├── file-input     (visually-hidden, drag/click 트리거)
  │     └── drop-label / file-selected
  │
  ├── upload-settings      (설정 패널)
  │     ├── setting-row    회의 유형 select (10종)
  │     └── setting-row    참고파일 첨부 (MD/TXT/PDF)
  │
  └── upload-actions       (버튼 영역)
        ├── btn-primary    "분석 시작" (handleStart)
        └── btn-ghost      "초기화"
```

**`UploadParams` 인터페이스:**
```typescript
interface UploadParams {
  file: File
  meetingType: string
  refText: string     // readFileAsText() 결과 (PDF는 플레이스홀더)
}
```

---

#### `ProgressLog.tsx`

```
progress-log
  ├── gauge-section
  │     ├── 전체 게이지 (overall %)
  │     └── 단계 게이지 (stage_pct %) + stage_label + ETA
  └── log-container
        └── log-line × N  (SSE 로그 메시지)
```

---

#### `ResultTabs.tsx`

```
tabs
  ├── tab-bar
  │     ├── 📌 AI 회의록 요약
  │     ├── 🗣️ 화자별 스크립트
  │     └── 📄 전체 원문
  └── tab-content
        ├── tab-actions
        │     ├── CopyButton     클립보드 복사
        │     └── DownloadButton Blob URL → <a> 클릭 → 파일 저장
        └── result-area (textarea readonly) / ReactMarkdown
```

**다운로드 파일명:**

| 탭 | 저장 파일명 |
|---|---|
| AI 회의록 요약 | `meeting-summary.md` |
| 화자별 스크립트 | `speaker-script.txt` |
| 전체 원문 | `full-transcript.txt` |

---

## 5. 의존성 (`pyproject.toml`)

### 5-1. 주요 패키지

| 패키지 | 버전 | 역할 |
|---|---|---|
| `fastapi` | ≥0.115.0 | 웹 프레임워크 |
| `uvicorn[standard]` | ≥0.32.0 | ASGI 서버 |
| `sse-starlette` | ≥2.0.0 | SSE EventSourceResponse |
| `aiofiles` | ≥24.1.0 | 비동기 파일 I/O |
| `python-multipart` | ≥0.0.12 | multipart/form-data 파싱 |
| `faster-whisper` | ≥1.0.0 | CPU STT |
| `whisperx` | 3.8.5+ | 화자 분리 + 정렬 |
| `torch` | 2.8.0+cpu | PyTorch CPU 빌드 |
| `torchaudio` | 2.8.0+cpu | 오디오 처리 |
| `ffmpeg-python` | ≥0.2.0 | FFmpeg Python 바인딩 |
| `google-genai` | ≥0.1.0 | Gemini API 클라이언트 |
| `python-dotenv` | ≥1.0.0 | .env 파일 로딩 |

### 5-2. PyTorch CPU 인덱스 설정

```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch      = { index = "pytorch-cpu" }
torchaudio = { index = "pytorch-cpu" }
```

### 5-3. torchcodec Windows 제한

```toml
[tool.uv]
override-dependencies = [
    # pyannote-audio 4.x 의존성이지만 Windows에서 DLL 로드 실패
    # Linux x86_64 / macOS에서만 설치
    "torchcodec>=0.6.0,<0.8.0; (sys_platform == 'linux' and platform_machine == 'x86_64') or sys_platform == 'darwin'",
]
```

---

## 6. 환경 변수 (`.env`)

파일 위치: `audio_extractor_stt/.env`

| 변수 | 필수 | 설명 |
|---|---|---|
| `MINUTE_SECOND_API_KEY` | ✅ | Gemini API 키 ([Google AI Studio](https://aistudio.google.com/app/apikey) 발급) |
| `HF_TOKEN` | — | Hugging Face 액세스 토큰 — pyannote 화자 분리 모델 라이선스 수락 필요 |

> **HF_TOKEN 없이 실행 시**: STT는 정상 동작, 화자 분리 건너뜀 → `speaker_text`가 전체 원문과 동일하게 반환됩니다.

---

## 7. 알려진 제약 사항

| 항목 | 내용 |
|---|---|
| 동시 처리 | 단일 사용자 전제 — in-memory job store, 다중 사용자 미지원 |
| 파일 크기 | 청크 업로드로 2 GB+ 지원하나, 처리 시간은 파일 길이 비례 증가 |
| 언어 | STT `language="ko"` 고정 — 한국어 최적화, 다국어 미지원 |
| Windows torchcodec | pyannote 4.x 의존성 — `pyproject.toml` override로 차단 (Windows에서 DLL 로드 실패) |
| 결과 영속성 | 서버 재시작 시 잡 결과 소멸 — 다운로드 또는 별도 저장 필요 |
