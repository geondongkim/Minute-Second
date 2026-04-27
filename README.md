# Minute Second

동영상 파일을 업로드하면 오디오를 추출하고, 음성을 텍스트로 변환한 뒤, LLM으로 회의록을 자동 생성하는 웹 서비스입니다.  
또한 **Teams Captions Saver KR** Chrome/Edge 확장을 포함하여, 실시간 MS Teams 자막을 캡처하고 AI로 요약할 수 있습니다.

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
| 실시간 뷰어 | 별도 탭에서 자막 실시간 확인, 검색, 발화자 필터 |
| 세션 히스토리 | 최근 10회 세션 저장 및 다시 보기 |

### 설치

1. `teams-caption-saver/` 폴더를 Chrome/Edge `chrome://extensions/` > **압축 해제된 확장 로드**로 등록
2. `manifest.json` 기준 Manifest V3

### 팝업 구성 (4탭)

- **캡처**: 현재 상태, 문장 수/경과/참석자, 지금 저장, 뷰어 열기, 자동저장 토글
- **설정**: 자막 자동 켜기, 회의 종료 시 자동 저장, 참석자 추적, 포맷, 폴더, 발화자 별칭
- **AI 요약**: Gemini/OpenAI API 키 입력, 모델 선택, 회의 유형별/커스텀 프롬프트
- **히스토리**: 세션 목록 → 클릭 시 뷰어에서 다시 보기

---

## Minute Second 웹 서비스

### 기능

- **동영상 업로드**: MP4 파일 업로드 (최대 2GB)
- **오디오 추출**: FFmpeg로 WAV 변환 (16kHz, 모노)
- **음성 인식 (STT)**: WhisperX + 화자 분리 (pyannote.audio)
- **회의록 요약**: Gemini API

### 실행 방법

```bash
# 환경 변수 설정 (.env 파일)
GEMINI_API_KEY=your_key_here
HF_TOKEN=your_huggingface_token_here

# 앱 실행
uv run streamlit run app.py
```

### 요구 사항

- Python 3.10+
- FFmpeg (PATH에 등록)
- GEMINI_API_KEY, HF_TOKEN

### 프로젝트 구조

```
app.py                          # Streamlit UI (레거시)
audio_extractor.py              # FFmpeg 오디오 추출
stt_processor.py                # WhisperX STT + 화자 분리
summarizer.py                   # Gemini API 요약
teams-caption-saver/            # Chrome/Edge 확장 v2.0
  manifest.json                 # MV3, permissions
  content_script.js             # 자막 감지 + 참석자 추적
  service_worker.js             # 저장, 배지, 세션 히스토리
  popup.html / popup.js         # 4탭 팝업 UI
  viewer.html / viewer.js       # 실시간 자막 뷰어
```
