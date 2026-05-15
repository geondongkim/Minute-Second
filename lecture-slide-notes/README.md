# Lecture Slide Notes

Vimeo, YouTube 또는 로컬 동영상에서 슬라이드 전환을 감지해 PNG, searchable PDF, NotebookLM 친화 Markdown을 생성하는 로컬 처리 엔진입니다.

이 패키지는 `repo/local_tools/video_to_slidenote_markdown.py`에서 검증한 실험 코드를 추적 가능한 독립 프로젝트로 승격하는 첫 구현입니다. CLI를 1차 실행 경로로 두고, 같은 코어 엔진을 MCP 서버와 Codex Skill/Plugin에서 재사용하도록 설계합니다.

## 현재 포함된 기능

- Vimeo player/course URL 해석 및 yt-dlp 다운로드 준비
- YouTube watch/short/embed URL 해석 및 같은 yt-dlp 다운로드 경로 재사용
- 로컬 동영상 슬라이드 안정 구간 감지
- 분석용 PNG와 PDF용 고해상도 PNG 분리 생성
- Tesseract OCR adapter 기반 OCR 텍스트 추출
- OCR 우선 + Gemini 보정용 adapter
- NotebookLM 친화 Markdown 생성
- searchable PDF 생성
- Codex/VS Code Copilot 연결을 위한 MCP 서버 골격

## 설치

```powershell
cd lecture-slide-notes
uv sync --extra ocr --extra mcp

# 개발/검증까지 포함할 때
uv sync --extra dev --extra ocr --extra mcp
```

필수 외부 도구:

- FFmpeg / FFprobe
- yt-dlp Python package 또는 이 패키지 의존성
- OCR을 사용할 경우 Tesseract binary와 `kor`, `eng` language data
- Gemini 보정을 사용할 경우 `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`

## 사용 예시

로컬 동영상 처리:

```powershell
uv run lecture-slide-notes process-video ..\videos\lecture.mp4 --output ..\outputs\lecture
```

Vimeo player URL 처리:

```powershell
uv run lecture-slide-notes process-url "https://player.vimeo.com/video/1170307610" --referer "https://academy.example/lesson" --output-root ..\outputs
```

YouTube URL 처리:

```powershell
uv run lecture-slide-notes process-url "https://www.youtube.com/watch?v=<id>" --output-root ..\outputs
```

환경 점검:

```powershell
uv run lecture-slide-notes doctor
```

## 출력 구조

```text
outputs/<lecture-slug>/
  slides/                    분석용 PNG
  slides_pdf/                PDF용 고해상도 PNG
  ocr_text/                  슬라이드별 OCR 원문
  contact_sheet.jpg          빠른 검수용 썸네일 모음
  slides_manifest.json       추출 메타데이터
  <lecture-slug>_notes.md    NotebookLM 친화 Markdown
  <lecture-slug>_slides.pdf  searchable PDF
```

## Codex/MCP 방향

MCP stdio 서버 entrypoint는 다음 명령으로 제공합니다.

```powershell
uv run lecture-slide-notes-mcp
```

Codex Skill과 Plugin은 같은 MCP 도구를 호출하게 만들어, 사용자가 “이 Vimeo/YouTube 강의를 NotebookLM용 자료로 만들어줘”라고 요청하면 다운로드부터 PDF/Markdown 생성까지 자동 실행되게 합니다.

## 검증

```powershell
uv run pytest
uv run ruff check
```
