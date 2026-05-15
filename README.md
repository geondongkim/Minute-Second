# Minute Second

> AI 기반 회의록 자동화 도구 모음 — 세 개의 독립 프로젝트와 umbrella 문서로 구성

| 서비스 | 설명 | 문서 |
|---|---|---|
| `Minute-Second-Audio-Extractor-STT` | 동영상 업로드 → 오디오 추출 → STT + 화자 분리 → AI 요약 (FastAPI + React + WhisperX + Gemini) | [repo](https://github.com/geondongkim/Minute-Second-Audio-Extractor-STT) |
| `Minute-Second-Caption-Saver` | MS Teams 실시간 자막과 Vimeo 강의 자막 캡처 + AI 요약 Chrome/Edge 확장 (Manifest V3, slide-notes CLI와 호환) | [repo](https://github.com/geondongkim/Minute-Second-Caption-Saver) |
| `Minute-Second-Lecture-Slide-Notes` | Vimeo/YouTube/로컬 강의 영상 → 슬라이드 PNG → searchable PDF + NotebookLM Markdown (CLI + MCP) | [repo](https://github.com/geondongkim/Minute-Second-Lecture-Slide-Notes) |

현재 이 리포지토리는 umbrella 문서와 분리/호환 계약을 관리합니다. 세 프로젝트 폴더는 각 `Minute-Second-*` 리포지토리를 가리키는 git submodule입니다.

```powershell
git clone --recurse-submodules https://github.com/geondongkim/Minute-Second.git
git submodule update --init --recursive
```

아키텍처 및 개발 가이드는 [`docs/`](docs/) 폴더를 참고하세요.

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 전체 시스템 아키텍처 및 데이터 흐름 |
| [docs/audio-extractor-stt.md](docs/audio-extractor-stt.md) | FastAPI + React 서비스 상세 설계 |
| [docs/teams-caption-saver.md](docs/teams-caption-saver.md) | Chrome 확장 상세 설계 |
| [docs/lecture-slide-notes.md](docs/lecture-slide-notes.md) | Vimeo/YouTube 강의 슬라이드 노트 생성기 설계 |
| [docs/repository-split.md](docs/repository-split.md) | 독립 리포지토리 분리 계획과 호환 계약 |
| [docs/development-guide.md](docs/development-guide.md) | 개발 환경 설정 및 실행 가이드 |

