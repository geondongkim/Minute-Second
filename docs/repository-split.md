# Minute Second 리포지토리 분리 계획

현재 루트 리포지토리는 `Minute-Second` umbrella 역할만 남기고, 실제 제품 코드는 아래 세 리포지토리로 분리합니다. 모든 이름에는 `Minute Second` 브랜드가 남도록 `Minute-Second-*` 접두사를 사용합니다.

| 대상 리포지토리 | 현재 경로 | 역할 |
|---|---|---|
| `Minute-Second-Audio-Extractor-STT` | `audio_extractor_stt/` | 동영상 업로드, STT, 화자 분리, 회의록/요약 웹 서비스 |
| `Minute-Second-Lecture-Slide-Notes` | `lecture-slide-notes/` | Vimeo/YouTube/로컬 강의 영상에서 슬라이드 PDF와 NotebookLM Markdown 생성 |
| `Minute-Second-Caption-Saver` | `teams-caption-saver/` | Teams/Vimeo 브라우저 캡션 캡처 확장 |

## 분리 원칙

- `repo/`, `result/`, `results/`, `videos/`, `.venv/`, `.env`는 로컬 전용 또는 생성 산출물이므로 어떤 분리 리포지토리에도 강제로 포함하지 않습니다.
- 각 프로젝트는 독립 실행 가능한 README, 의존성 파일, 검증 명령을 가져야 합니다.
- 브라우저 확장은 `lecture-slide-notes`의 내부 파일을 직접 호출하지 않고 CLI 계약만 호출합니다.
- repo 간 연동은 파일 경로 하드코딩보다 설정 가능한 경로와 안정적인 CLI/MCP 명령을 우선합니다.
- root `Minute-Second`는 문서, 호환 계약, release orchestration, split script만 보유하는 umbrella repo로 축소합니다.

## 호환 계약

### Caption Saver -> Lecture Slide Notes

브라우저 확장은 Vimeo/HLS 상태를 감지한 뒤 로컬 PowerShell 명령을 복사합니다. 분리 후에도 아래 CLI 계약만 유지하면 됩니다.

```powershell
uv run --project <lecture-slide-notes-repo> lecture-slide-notes process-url <url> --output-root <output-root> [--referer <lesson-url>] [--title <title>]
uv run --project <lecture-slide-notes-repo> lecture-slide-notes process-video <video-file> --output <output-dir>
```

확장은 `chrome.storage.sync`의 아래 키를 읽어 분리 repo 위치를 바꿀 수 있습니다.

| storage key | 기본값 | 설명 |
|---|---|---|
| `lectureSlideNotesProjectPath` | `.\lecture-slide-notes` | `Minute-Second-Lecture-Slide-Notes` 로컬 checkout 경로 |
| `lectureSlideNotesVideosDir` | `.\videos` | 다운로드 영상 저장 위치 |
| `lectureSlideNotesOutputRoot` | `.\repo\slidenote_video_exports` | PDF/Markdown 생성 위치 |

### Lecture Slide Notes 입력 source

`lecture-slide-notes`는 Vimeo가 현재 테스트베드이며, YouTube는 같은 yt-dlp 경로로 확장합니다.

- Vimeo: `player.vimeo.com/video/<id>` + optional `--referer`
- YouTube: `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`, `youtube.com/shorts/`, `youtube.com/live/`
- Local video: `process-video <path>`
- Course page: `process-url <lesson-url> --fetch-page`

## 분리 스크립트

안전한 기본 실행은 로컬 split repository만 생성합니다.

```powershell
.\tools\split-repositories.ps1 -Recreate
```

기본 출력 위치는 `..\Minute-Second-Repositories\`입니다.

원격 리포지토리가 준비되면 환경 변수로 URL을 주고 push합니다.

```powershell
$env:MINUTE_SECOND_AUDIO_REMOTE = "https://github.com/<owner>/Minute-Second-Audio-Extractor-STT.git"
$env:MINUTE_SECOND_SLIDE_NOTES_REMOTE = "https://github.com/<owner>/Minute-Second-Lecture-Slide-Notes.git"
$env:MINUTE_SECOND_CAPTION_REMOTE = "https://github.com/<owner>/Minute-Second-Caption-Saver.git"
.\tools\split-repositories.ps1 -Recreate -Push
```

## 전환 순서

1. 현재 monorepo 변경사항을 검증하고 commit/push합니다.
2. `tools/split-repositories.ps1 -Recreate`로 로컬 split repos를 생성합니다.
3. 각 split repo에서 README, 테스트, ignore 규칙이 단독으로 충분한지 확인합니다.
4. 새 원격 GitHub repos를 만들고 환경 변수에 URL을 설정합니다.
5. `tools/split-repositories.ps1 -Recreate -Push`로 각각 push합니다.
6. root repo에서는 세 프로젝트 폴더를 제거하고, 필요하면 submodule 또는 checkout 안내만 남깁니다.
