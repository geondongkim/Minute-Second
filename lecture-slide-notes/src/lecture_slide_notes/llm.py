from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class GeminiCorrector:
    model: str = "gemini-2.5-flash"
    api_key: str | None = None

    def is_available(self) -> bool:
        return bool(self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    def correct_slide_text(self, *, title: str, slide_number: int, timestamp: str, ocr_text: str) -> str:
        if not ocr_text.strip() or not self.is_available():
            return ""

        from google import genai

        api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are cleaning OCR output from a Korean lecture slide for NotebookLM.
Use the OCR text as the source of truth. Preserve technical terms, numbers, question choices, and Korean wording.
Do not invent missing facts. If text is uncertain, keep it conservative.

Lecture title: {title}
Slide: {slide_number}
Timestamp: {timestamp}

Return concise Markdown with these sections:
### Slide Summary
### Key Terms
### Corrected Slide Text

OCR text:
{ocr_text}
""".strip()
        response = client.models.generate_content(model=self.model, contents=prompt)
        return (getattr(response, "text", None) or "").strip()
