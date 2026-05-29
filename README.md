# Minute Second

Minute Second는 회의와 강의의 기록을 캡처하고, 전사하고, 복습 가능한 자료로 정리하는 로컬 도구 모음입니다. 이 루트 저장소는 세 개의 독립 프로젝트를 소개하는 정적 웹페이지와 로컬 clone 안내를 제공합니다.

## 프로젝트

| 프로젝트 | 역할 | 저장소 |
| --- | --- | --- |
| Script Saver | Teams 라이브 캡션과 Vimeo 강의 자막을 캡처하고 AI 요약까지 연결하는 Chrome/Edge 확장 | [Minute-Second-Script-Saver](https://github.com/geondongkim/Minute-Second-Script-Saver) |
| Audio Extractor STT | 동영상 업로드 후 오디오 추출, STT, 화자 분리, AI 회의록 생성을 처리하는 FastAPI + React 서비스 | [Minute-Second-Audio-Extractor-STT](https://github.com/geondongkim/Minute-Second-Audio-Extractor-STT) |
| Lecture Slide Notes | 강의 영상에서 슬라이드를 감지해 searchable PDF와 NotebookLM용 Markdown을 생성하는 로컬 CLI 엔진 | [Minute-Second-Lecture-Slide-Notes](https://github.com/geondongkim/Minute-Second-Lecture-Slide-Notes) |

## 웹페이지 보기

이 저장소는 빌드 과정이 없는 정적 사이트입니다.

```bash
open index.html
```

## 세 프로젝트 한 번에 가져오기

아래 명령은 `external/` 폴더에 세 프로젝트를 clone합니다. 이미 clone되어 있으면 `git pull --ff-only`로 최신 상태만 가져옵니다.

```bash
mkdir -p external

while read -r name url; do
  if [ -d "external/$name/.git" ]; then
    git -C "external/$name" pull --ff-only
  else
    git clone "$url" "external/$name"
  fi
done <<'REPOS'
Minute-Second-Script-Saver https://github.com/geondongkim/Minute-Second-Script-Saver.git
Minute-Second-Audio-Extractor-STT https://github.com/geondongkim/Minute-Second-Audio-Extractor-STT.git
Minute-Second-Lecture-Slide-Notes https://github.com/geondongkim/Minute-Second-Lecture-Slide-Notes.git
REPOS
```

`external/`은 루트 저장소에서 Git 추적을 하지 않도록 `.gitignore`에 등록되어 있습니다. 각 프로젝트의 의존성 설치와 실행은 해당 저장소의 README를 기준으로 진행합니다.

## 충돌 방지 설정

- 루트 `.gitignore`는 `external/`, `node_modules/`, `.venv/`, `.pytest_cache/`, `dist/`, `build/` 같은 로컬 산출물을 무시합니다.
- 루트 `pytest.ini`는 `external/`을 `norecursedirs`에 포함해 하위 프로젝트 테스트가 루트 pytest 수집에 섞이지 않도록 합니다.
