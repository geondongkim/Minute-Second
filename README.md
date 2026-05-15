# Minute Second

> 회의와 강의에서 생기는 음성, 스크립트, 슬라이드를 저장하고 정리하는 public project gateway.

Minute Second는 세 개의 독립 public repository로 나뉘어 있습니다. 이 root repository는 각 프로젝트로 들어가는 랜딩 페이지이자, submodule 기반 통합 workspace입니다.

## Projects

| Project | Use It For | Public Repo |
|---|---|---|
| `Minute-Second-Audio-Extractor-STT` | 동영상 업로드, 오디오 추출, 한국어 STT, 화자 분리, AI 회의록 생성 | [GitHub](https://github.com/geondongkim/Minute-Second-Audio-Extractor-STT) |
| `Minute-Second-Script-Saver` | Teams 회의 캡션과 Vimeo 강의 자막 저장, AI 요약, slide-notes 명령 복사 | [GitHub](https://github.com/geondongkim/Minute-Second-Script-Saver) |
| `Minute-Second-Lecture-Slide-Notes` | Vimeo, YouTube, 로컬 강의 영상에서 슬라이드 PNG, searchable PDF, NotebookLM Markdown 생성 | [GitHub](https://github.com/geondongkim/Minute-Second-Lecture-Slide-Notes) |

## Routes

| Goal | Start Here |
|---|---|
| 동영상 파일을 회의록으로 만들기 | `Minute-Second-Audio-Extractor-STT` |
| 브라우저에서 회의/강의 스크립트를 저장하기 | `Minute-Second-Script-Saver` |
| 강의 영상을 PDF/Markdown 학습 자료로 바꾸기 | `Minute-Second-Lecture-Slide-Notes` |
| 세 프로젝트를 함께 보고 연동 흐름을 확인하기 | 이 repository의 submodules |

## Architecture Map

```text
Minute-Second
  -> Audio Extractor STT
	  video file -> audio -> STT/diarization -> AI meeting notes

  -> Script Saver
	  browser captions/subtitles -> saved sessions -> AI summaries
												-> lecture-slide-notes CLI commands

  -> Lecture Slide Notes
	  Vimeo/YouTube/local video -> slide PNGs -> searchable PDF + NotebookLM Markdown
```

## Local Workspace

```powershell
git clone --recurse-submodules https://github.com/geondongkim/Minute-Second.git
cd Minute-Second
git submodule update --init --recursive
```

To refresh all project pointers:

```powershell
.\tools\update-submodules.ps1
```

The detailed docs live inside each public project repository. This root keeps only the gateway map, submodule pointers, and lightweight orchestration helpers.

Open [index.html](index.html) for the static landing page.

More root context: [docs/repository-map.md](docs/repository-map.md)

