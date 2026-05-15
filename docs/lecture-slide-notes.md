# lecture-slide-notes — 강의 슬라이드 노트 생성기

`lecture-slide-notes/`는 Vimeo, YouTube 또는 로컬 강의 영상을 입력으로 받아 슬라이드 PNG, searchable PDF, NotebookLM 친화 Markdown을 생성하는 로컬 처리 엔진입니다. 현재 테스트베드는 Vimeo이지만, 다운로드 계층은 yt-dlp 기반이라 YouTube를 같은 경로로 확장합니다.

## 목표

- 강의 사이트의 Vimeo player URL, YouTube URL 또는 로컬 동영상 파일을 처리합니다.
- 슬라이드 전환이 끝난 안정 구간만 선택해 transition frame을 줄입니다.
- 분석용 PNG와 PDF용 고화질 PNG를 분리합니다.
- 실제 OCR 텍스트를 우선 추출하고, 필요하면 Gemini가 구조화/보정합니다.
- Markdown과 searchable PDF를 함께 생성해 NotebookLM 업로드에 적합하게 만듭니다.
- 같은 코어 엔진을 CLI, 데스크톱 UI, MCP, Codex Skill/Plugin에서 재사용합니다.

## 파일 구조

```text
lecture-slide-notes/
  pyproject.toml
  README.md
  src/lecture_slide_notes/
    cli.py              argparse 기반 CLI
    sources.py          Vimeo/YouTube/course/local source resolver
    downloader.py       yt-dlp 다운로드/metadata 추출
    slides.py           ffmpeg sampling + stable slide detection
    ocr.py              OCR adapter
    llm.py              Gemini 보정 adapter
    markdown.py         NotebookLM Markdown builder
    pdf.py              searchable PDF writer
    pipeline.py         end-to-end orchestration
    mcp_server.py       MCP server entrypoint
    doctor.py           환경 점검
```

## 처리 흐름

```text
URL 또는 동영상 파일
  -> SourceResolver
  -> yt-dlp DownloadManager 또는 local file
  -> ffmpeg frame sampling
  -> stable-run slide selection
  -> slides/ + slides_pdf/
  -> OCR extraction
  -> optional Gemini correction
  -> NotebookLM Markdown
  -> searchable PDF
  -> manifest + contact sheet
```

## 입력 URL 처리 원칙

### Vimeo

1. 강의 페이지에서 `iframe[src*="player.vimeo.com/video/"]`를 찾습니다.
2. player URL과 강의 페이지 URL을 referer로 함께 보관합니다.
3. direct `.m3u8` 또는 `playlist.json`은 fallback으로만 사용합니다.
4. 실제 다운로드는 가능하면 yt-dlp의 Vimeo extractor가 처리하게 합니다.
5. 로그인 강의 사이트는 `--cookies-from-browser chrome|edge` 또는 cookie file만 사용하고 비밀번호를 저장하지 않습니다.
6. DRM/Widevine 등 보호 스트림은 지원하지 않습니다.

### YouTube

1. `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`, `youtube.com/shorts/`, `youtube.com/live/` 형식을 인식합니다.
2. 내부적으로 canonical watch URL인 `https://www.youtube.com/watch?v=<id>`로 정리합니다.
3. 다운로드와 metadata 추출은 Vimeo와 동일하게 yt-dlp extractor에 맡깁니다.
4. 강의 사이트에 YouTube iframe이 들어간 경우 `SourceResolver(fetch_page=True)`가 embed URL을 찾아 YouTube source로 전환합니다.
5. 자막, 챕터, playlist 처리 등 YouTube 전용 기능은 Phase 2 이후 별도 옵션으로 추가합니다.

## CLI

```powershell
cd lecture-slide-notes
uv sync --extra ocr --extra mcp
uv run lecture-slide-notes doctor
uv run lecture-slide-notes process-video ..\videos\lecture.mp4 --output ..\outputs\lecture
uv run lecture-slide-notes process-url "https://player.vimeo.com/video/<id>" --referer "https://academy.example/lesson" --output-root ..\outputs
uv run lecture-slide-notes process-url "https://www.youtube.com/watch?v=<id>" --output-root ..\outputs
```

## Codex/MCP 확장

Phase 2에서는 `lecture_slide_notes.mcp_server`를 stdio MCP 서버로 등록하고, `.agents/skills/lecture-slide-notes/SKILL.md`가 해당 도구를 사용하는 지침을 제공합니다. 이때 YouTube URL은 별도 도구가 아니라 `process-url` 입력 source type으로 처리합니다. Phase 3에서는 Skill, MCP 설정, hooks, 메타데이터를 묶은 Codex Plugin으로 배포할 수 있게 합니다.

## 검증

- `doctor`로 FFmpeg, FFprobe, Tesseract, Python package, Gemini key를 확인합니다.
- `tests/test_sources.py`는 Vimeo URL, YouTube URL/iframe, manifest 파싱을 검증합니다.
- 실제 영상 검증은 짧은 fixture부터 시작해 슬라이드 수, PDF 페이지 수, PyMuPDF 텍스트 추출 길이를 확인합니다.
