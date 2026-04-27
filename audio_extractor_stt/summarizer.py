from google import genai
import os

# ─── 회의 유형별 기본 지시 ────────────────────────────────────────────────────

_MEETING_PROMPTS: dict[str, str] = {
    "general": (
        "다음 회의/영상의 전체 텍스트를 한국어로 구조화하여 요약하세요. "
        "주요 결정사항, 핵심 논의사항, 액션아이템을 포함하세요."
    ),
    "standup": (
        "다음 스탠드업 회의를 요약하세요. "
        "각 참여자의 어제 한 일, 오늘 할 일, 블로커를 표로 정리하세요."
    ),
    "retro": (
        "다음 회고 회의를 요약하세요. "
        "잘 된 점(Keep), 개선할 점(Problem), 액션아이템(Try) 형식으로 정리하세요."
    ),
    "planning": (
        "다음 플래닝 회의를 요약하세요. "
        "스프린트 목표, 작업 목록, 예상 이슈를 정리하세요."
    ),
    "executive": (
        "다음 경영진 회의를 요약하세요. "
        "핵심 결정사항, 주요 지표, 후속 조치에 집중하세요."
    ),
    "interview": (
        "다음 인터뷰를 요약하세요. "
        "주요 답변, 강점, 우려 사항, 면접관 평가를 정리하세요."
    ),
    "brainstorm": (
        "다음 브레인스토밍 회의를 요약하세요. "
        "제시된 아이디어를 카테고리별로 정리하고 우선순위를 제안하세요."
    ),
    "review": (
        "다음 리뷰 회의를 요약하세요. "
        "검토된 내용, 결정사항, 수정 요청, 후속 조치를 정리하세요."
    ),
    "1on1": (
        "다음 1:1 미팅을 요약하세요. "
        "논의된 업무, 성장 계획, 피드백, 다음 액션아이템을 정리하세요."
    ),
    "lecture": (
        "다음 라이브 강의 내용을 한국어로 요약하세요. "
        "강의 주제, 핵심 개념 설명, 주요 예시, Q&A 내용(있는 경우), "
        "학습 포인트를 체계적으로 정리하세요."
    ),
}

_DEFAULT_PROMPT = _MEETING_PROMPTS["general"]

_OUTPUT_STRUCTURE = """
아래의 세 가지 섹션으로 나누어 마크다운 포맷으로 작성하세요:

## 📌 주요 안건
## 🗣️ 핵심 논의 내용
## ✅ Action Item (담당자 및 기한)
"""


def summarize_text(
    text: str,
    meeting_type: str = "general",
    ref_text: str = "",
) -> str:
    """
    텍스트를 AI로 요약합니다.

    Args:
        text: STT로 변환된 전체 텍스트
        meeting_type: 회의 유형 키 (general, standup, retro, ...)
        ref_text: 참고자료 텍스트 (선택)
    """
    api_key = os.environ.get("MINUTE_SECOND_API_KEY")
    if not api_key:
        return "Error: MINUTE_SECOND_API_KEY environment variable not set."

    model_name = "gemini-3.1-flash-lite-preview"
    client = genai.Client(api_key=api_key)

    base_instruction = _MEETING_PROMPTS.get(meeting_type, _DEFAULT_PROMPT)

    ref_section = ""
    if ref_text and ref_text.strip():
        ref_section = f"\n\n[참고자료]\n{'─' * 40}\n{ref_text.strip()}\n{'─' * 40}\n"

    prompt = (
        f"{base_instruction}\n"
        f"{_OUTPUT_STRUCTURE}"
        f"{ref_section}\n"
        f"[전체 텍스트]\n{'─' * 40}\n{text}\n{'─' * 40}"
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"요약 중 오류가 발생했습니다 ({model_name}): {str(e)}"

