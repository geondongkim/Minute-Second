# Minute Second

이 저장소는 두 개의 독립 프로젝트로 구성됩니다.

| 디렉터리 | 설명 |
|---|---|
| `audio_extractor_stt/` | 동영상 → STT → 회의록 웹 서비스 (FastAPI + WhisperX + Gemini) |
| `teams-caption-saver/` | MS Teams 실시간 자막 캡처 + AI 요약 Chrome/Edge 확장 |

---

## Teams Captions Saver KR (`teams-caption-saver/`)

MS Teams 실시간 자막(라이브 캡션)을 자동 저장하는 Chrome/Edge 확장 v2.0.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 실시간 캡처 | MutationObserver로 Teams 자막 DOM 감지, 발화 완료 시 저장 |
| 자막 자동 켜기 | 회의 참여 시 라이브 캡션 자동 활성화 |
| 참석자 추적 | 참석자 목록 실시간 추적 및 보고서 생성 |
| 자동 저장 | 5분 주기 + 회의 종료 시 자동 저장 |
| 다양한 포맷 | Markdown / TXT / JSON 선택 저장 |
| 발화자 별칭 | 이름 치환 기능 |
| AI 요약 | Gemini/OpenAI API를 이용한 회의 유형별 요약 |
| 실시간 뷰어 | 3탭 뷰어 — 원문 / 발화자별 / AI 요약 (참고파일 첨부 지원) |
| 세션 히스토리 | 최근 10회 세션 저장 및 다시 보기 |

### 설치

1. `teams-caption-saver/` 폴더를 Chrome/Edge `chrome://extensions/` > **압축 해제된 확장 로드**로 등록
2. `manifest.json` 기준 Manifest V3

### 팝업 구성 (4탭)

- **캡처**: 현재 상태, 문장 수/경과/참석자, 지금 저장, 뷰어 열기, 자동저장 토글
- **설정**: 자막 자동 켜기, 회의 종료 시 자동 저장, 참석자 추적, 포맷, 폴더, 발화자 별칭
- **AI 요약**: Gemini/OpenAI API 키 입력, 모델 선택, 회의 유형별/커스텀 프롬프트
- **히스토리**: 세션 목록 → 클릭 시 뷰어에서 다시 보기

### 뷰어 (`viewer.html`) — 3탭 구성

- **📄 원문**: 발화자 필터 + 검색 + 자막 목록 (LIVE 실시간 업데이트)
- **🗣️ 발화자별**: 발화자 그룹별 대화 목록
- **📌 AI 요약**: AI 설정 (편집 가능) + 회의유형 선택 + 참고파일 첨부(MD/TXT/PDF) + 3섹션 결과

---

## Minute Second 웹 서비스 (`audio_extractor_stt/`)

### 기능

- **동영상 업로드**: MP4 파일 업로드 (최대 2GB)
- **오디오 추출**: FFmpeg로 WAV 변환 (16kHz, 모노)
- **음성 인식 (STT)**: WhisperX + 화자 분리 (pyannote.audio)
- **회의록 요약**: Gemini API

### 실행 방법

```bash
cd audio_extractor_stt

# 최초 실행 시 venv 생성
uv sync

# 앱 실행
uv run streamlit run main.py
```

### 요구 사항

- Python 3.10+
- FFmpeg (PATH에 등록)
- `audio_extractor_stt/.env`: `GEMINI_API_KEY`, `HF_TOKEN`

### 프로젝트 구조

```
audio_extractor_stt/
  main.py                       # Streamlit UI 진입점
  audio_extractor.py            # FFmpeg 오디오 추출
  stt_processor.py              # WhisperX STT + 화자 분리
  summarizer.py                 # Gemini API 요약
  pyproject.toml / uv.lock      # uv 패키지 관리

teams-caption-saver/
  manifest.json                 # MV3, permissions
  content_script.js             # 자막 감지 + 참석자 추적
  service_worker.js             # 저장, 배지, 세션 히스토리
  popup.html / popup.js         # 4탭 팝업 UI
  viewer.html / viewer.js       # 3탭 자막 뷰어 (AI 요약 + 참고파일)
  pdf.min.js / pdf.worker.min.js # PDF.js 3.11.174 (참고파일 PDF 파싱)
```
