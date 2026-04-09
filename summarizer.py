from google import genai
import os

def summarize_text(text: str) -> str:
    """
    Summarize the given text using the Gemini 3.1 Flash Lite model.
    """
    api_key = os.environ.get("MINUTE_SECOND_API_KEY")
    if not api_key:
        return "Error: MINUTE_SECOND_API_KEY environment variable not set."

    model_name = "gemini-3.1-flash-lite-preview"
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""다음은 회의 또는 동영상의 전체 텍스트 내용입니다. 
다음 텍스트를 기반으로 아래의 세 가지 요소로 나누어 구조화된 마크다운 포맷으로 요약해주세요.

## 📌 주요 안건
## 🗣️ 핵심 논의 내용
## ✅ Action Item (담당자 및 기한)

텍스트:
{text}
"""
    try:
        # Note: Thinking level low isn't officially explicitly parameterizable in basic generate_content yet, so we just use the fast model.
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"요약 중 오류가 발생했습니다 ({model_name}): {str(e)}"
