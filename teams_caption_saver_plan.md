# Teams Live Captions Saver — 구현 계획

## 개요

MS Teams 웹 버전에서 실시간 자막(Live Captions)을 캡처하여 텍스트로 저장하는 **Edge/Chrome 확장 프로그램** 구현.
저장된 트랜스크립트는 기존 `summarizer.py` (Gemini API) 파이프라인에 입력하여 회의 요약까지 자동화.

---

## 레퍼런스 분석 결과

**클론 위치**: `repo/Live-Captions-Saver/`

### 핵심 DOM 셀렉터 (Teams 웹 v2)

| 요소 | 셀렉터 |
|------|--------|
| 자막 컨테이너 | `[data-tid='closed-caption-v2-window-wrapper']`, `[data-tid='closed-captions-renderer']` |
| 자막 메시지 행 | `.fui-ChatMessageCompact` |
| 발화자 이름 | `[data-tid="author"]` |
| 자막 텍스트 | `[data-tid="closed-caption-text"]` |
| 통화 종료 버튼 | `button[data-tid='hangup-main-btn']` |
| 더보기 버튼 | `button[data-tid='more-button']` |
| 자막 켜기 버튼 | `div[id='closed-captions-button']` |

> **참고**: Teams UI는 업데이트마다 DOM이 바뀔 수 있음. `data-tid` 속성이 가장 안정적 (CSS 클래스보다 훨씬 변경 빈도 낮음).

---

## 아키텍처

```
repo/Live-Captions-Saver/          ← 레퍼런스 (건드리지 않음)
teams-caption-saver/               ← 우리가 만들 확장 프로그램
├── manifest.json                  ← Manifest V3, 권한 선언
├── content_script.js              ← MutationObserver로 자막 DOM 감시
├── popup.html                     ← 시작/중지/저장 UI
├── popup.js                       ← 팝업 로직
├── service_worker.js              ← 백그라운드 (메시지 라우팅)
└── icon.png                       ← 확장 아이콘
```

---

## 구현 단계

### Phase 1 — 핵심 캡처 기능 (MVP)

**목표**: 팀즈 회의 중 자막을 잡아서 TXT/MD로 저장

#### 1-1. `manifest.json`

```json
{
  "manifest_version": 3,
  "name": "Teams Captions Saver KR",
  "version": "1.0.0",
  "permissions": ["downloads", "storage"],
  "host_permissions": [
    "https://teams.microsoft.com/*",
    "https://teams.cloud.microsoft/*",
    "https://teams.live.com/*"
  ],
  "content_scripts": [{
    "matches": ["https://teams.microsoft.com/*", "https://teams.cloud.microsoft/*", "https://teams.live.com/*"],
    "js": ["content_script.js"]
  }],
  "action": { "default_popup": "popup.html" },
  "background": { "service_worker": "service_worker.js" }
}
```

#### 1-2. `content_script.js` (핵심 로직)

```
동작 흐름:
1. MutationObserver 설정
   - document.body 전체를 observe (subtree: true, childList: true, characterData: true)
   - 캡션 컨테이너가 DOM에 나타나면 → 내부 observe로 전환
2. 자막 행 처리 (processCaptions)
   - .fui-ChatMessageCompact 요소 순회
   - [data-tid="author"] → 발화자
   - [data-tid="closed-caption-text"] → 텍스트
   - data-caption-id 속성으로 중복 방지 (새 요소 vs 업데이트된 요소 구분)
3. 상태 저장
   - transcriptArray: [{Name, Text, Time, key}]
   - chrome.storage.session 에 주기적 백업 (5초마다)
4. 회의 종료 감지
   - hangup 버튼 클릭 이벤트 감지 → 자동 저장 옵션
```

#### 1-3. `popup.html` / `popup.js`

```
UI 구성:
- 상태 표시: "캡처 중... (47개 문장)" / "대기 중"
- 버튼: [저장 (TXT)] [저장 (MD)] [저장 (AI 형식)]
- 체크박스: "자막 자동 시작" / "회의 종료 시 자동 저장"

popup.js 동작:
- content_script에 메시지로 명령 전달 (captureState 토글)
- 저장 시 chrome.runtime.sendMessage → service_worker가 chrome.downloads.download() 호출
```

#### 1-4. `service_worker.js`

```
역할:
- popup ↔ content_script 간 메시지 브리지
- chrome.downloads.download() 실행 (content script는 직접 다운로드 불가)
- 세션 간 데이터 보존 (storage)
```

---

### Phase 2 — Minute_Second 파이프라인 연동

**목표**: 저장된 트랜스크립트 → 기존 Gemini 요약 자동 실행

#### 옵션 A: 파일 drop 방식 (간단)
1. 확장에서 `.txt` 파일 저장 → `results/` 폴더 또는 `videos/` 폴더에 drag & drop
2. 새 CLI 커맨드 `run_cli.py --transcript <file.txt>` 추가
   - `audio_extractor` 건너뜀
   - `stt_processor` 건너뜀
   - `summarizer.py` 직접 호출 (텍스트 입력)
   - 결과: `results/<제목>_transcript_<datetime>.md`

#### 옵션 B: 웹 UI 업로드 방식
1. FastAPI `POST /summarize-text` 엔드포인트 추가
2. 확장 팝업에서 "요약 요청" 버튼 → 텍스트를 localhost:8000으로 POST
3. Gemini 요약 결과 팝업에 표시 또는 파일로 저장

> **우선순위**: 옵션 A 먼저 구현 (단순), 이후 옵션 B 추가

---

### Phase 3 — 고급 기능 (선택)

- **화자명 별칭**: SPEAKER_00 → 실제 이름 매핑 (레퍼런스 참고)
- **자동 자막 켜기**: 회의 참여 시 자막 자동 활성화 버튼 클릭
- **실시간 뷰어**: 별도 팝업 창에서 실시간 트랜스크립트 표시

---

## 파일 구조 (구현 후)

```
Minute_Second/
├── teams-caption-saver/           ← 확장 프로그램 폴더
│   ├── manifest.json
│   ├── content_script.js
│   ├── popup.html
│   ├── popup.js
│   ├── service_worker.js
│   └── icon.png
├── repo/
│   └── Live-Captions-Saver/      ← 레퍼런스 (읽기 전용)
├── run_cli.py                     ← 기존 + --transcript 옵션 추가 (Phase 2)
└── ...
```

---

## 설치 방법 (개발자 모드)

1. `edge://extensions/` 접속
2. "개발자 모드" 켜기
3. "압축 해제된 확장 로드" → `teams-caption-saver/` 폴더 선택
4. `teams.microsoft.com` 에서 회의 참여 → 자막 켜기 → 팝업에서 저장

---

## 주의사항

- Teams UI는 업데이트 시 DOM 구조가 변경될 수 있음 → `data-tid` 속성 기반 셀렉터가 가장 안정적
- 회의 참가자 전원의 동의 필요 (녹음/전사 관련 법령 준수)
- 현재 Teams 웹 버전(`teams.microsoft.com/v2/`)만 지원 (v1 미지원)
- 로컬 처리만 수행 (외부 서버 전송 없음)

---

## 구현 우선순위

| 순서 | 항목 | 난이도 | 예상 시간 |
|------|------|--------|----------|
| 1 | DOM 셀렉터 검증 (Edge DevTools) | 낮음 | 30분 |
| 2 | `manifest.json` + 기본 구조 | 낮음 | 30분 |
| 3 | `content_script.js` (MutationObserver + 자막 파싱) | 중간 | 2시간 |
| 4 | `popup.html` + `popup.js` (저장 UI) | 낮음 | 1시간 |
| 5 | `service_worker.js` (다운로드 처리) | 낮음 | 30분 |
| 6 | 테스트 (실제 팀즈 회의) | - | 1시간 |
| 7 | `run_cli.py --transcript` (Phase 2) | 낮음 | 1시간 |
