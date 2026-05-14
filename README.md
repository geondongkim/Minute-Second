# Minute Second

> AI 기반 회의록 자동화 도구 모음 — 두 개의 독립 서비스로 구성

| 서비스 | 설명 | 문서 |
|---|---|---|
| `audio_extractor_stt/` | 동영상 업로드 → 오디오 추출 → STT + 화자 분리 → AI 요약 (FastAPI + React + WhisperX + Gemini) | [README](audio_extractor_stt/README.md) |
| `teams-caption-saver/` | MS Teams 실시간 자막과 Vimeo 강의 자막 캡처 + AI 요약 Chrome/Edge 확장 (Manifest V3) | [README](teams-caption-saver/README.md) |

아키텍처 및 개발 가이드는 [`docs/`](docs/) 폴더를 참고하세요.

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 전체 시스템 아키텍처 및 데이터 흐름 |
| [docs/audio-extractor-stt.md](docs/audio-extractor-stt.md) | FastAPI + React 서비스 상세 설계 |
| [docs/teams-caption-saver.md](docs/teams-caption-saver.md) | Chrome 확장 상세 설계 |
| [docs/development-guide.md](docs/development-guide.md) | 개발 환경 설정 및 실행 가이드 |

