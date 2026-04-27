"""
회의록 자동 생성 CLI

사용법:
  uv run python run_cli.py <video_file> [--output-dir results]

예시:
  uv run python run_cli.py "videos/1팀의 모임-20260406_091051-모임 녹음녹화.mp4"
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _progress(msg: str) -> None:
    # __PROGRESS__ 이벤트는 화면에 게이지로 표시
    if msg.startswith("__PROGRESS__:"):
        import json
        try:
            p = json.loads(msg[len("__PROGRESS__:"):])
            overall = p.get("overall", 0)
            stage = p.get("stage_label", "")
            stage_pct = p.get("stage_pct", 0)
            eta = p.get("eta_s")

            bar_len = 30
            filled = int(bar_len * overall / 100)
            bar = "█" * filled + "░" * (bar_len - filled)

            eta_str = ""
            if eta is not None and eta > 0:
                m, s = divmod(int(eta), 60)
                eta_str = f"  ETA {m}분 {s:02d}초" if m else f"  ETA {s}초"

            line = f"\r[{bar}] {overall:3d}%  {stage} ({stage_pct}%){eta_str}   "
            sys.stdout.write(line)
            sys.stdout.flush()
        except Exception:
            pass
    else:
        # 일반 로그는 게이지 아래 줄에 출력
        sys.stdout.write(f"\n  → {msg}")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="동영상 → 자동 회의록 (Markdown)")
    parser.add_argument("video", help="처리할 동영상 파일 경로")
    parser.add_argument(
        "--output-dir", "-o",
        default="results",
        help="결과 .md 파일을 저장할 디렉터리 (기본: results/)",
    )
    parser.add_argument(
        "--no-diarize",
        action="store_true",
        help="화자 분리 건너뜀 (빠른 처리 / 비교용)",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {video_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 결과 파일명: 원본 파일명 + 타임스탬프.md
    stem = video_path.stem
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    diarize = not args.no_diarize
    suffix = "" if diarize else "_no_diarize"
    output_path = output_dir / f"{stem}_{timestamp}{suffix}.md"

    print(f"📹 입력 파일: {video_path}")
    print(f"📄 출력 파일: {output_path}")
    if not diarize:
        print("⚡ 화자 분리: 건너뜀 (--no-diarize)")
    print("-" * 60)

    start = time.monotonic()

    # ── 1단계: 오디오 추출 ──────────────────────────────────────
    from audio_extractor import extract_audio_from_video
    from stt_processor import process_audio
    from summarizer import summarize_text

    print("\n🎵 [1/3] 오디오 추출 중...")
    with extract_audio_from_video(str(video_path)) as audio_path:
        print(f"  → 임시 오디오: {audio_path}")

        # ── 2단계: STT + 화자 분리 ─────────────────────────────
        label = "STT 시작..." if diarize else "STT 시작 (화자분리 없음)..."
        print(f"\n🔤 [2/3] {label}")
        combined_text, speaker_text = process_audio(audio_path, _progress, diarize=diarize)

    print()  # 게이지 줄 끝 처리

    # ── 3단계: AI 요약 ──────────────────────────────────────────
    print("\n✨ [3/3] AI 회의록 요약 생성 중...")
    summary = summarize_text(combined_text)

    # ── 결과 저장 ────────────────────────────────────────────────
    elapsed = time.monotonic() - start
    m, s = divmod(int(elapsed), 60)
    elapsed_str = f"{m}분 {s}초" if m else f"{s}초"

    md_content = f"""# 회의록: {video_path.name}

> 생성일시: {time.strftime("%Y-%m-%d %H:%M:%S")}  
> 처리 소요시간: {elapsed_str}  
> 화자 분리: {"✅ 포함" if diarize else "❌ 미포함 (--no-diarize)"}

---

{summary}

---

## 🗣️ {"화자별 발화 내역" if diarize else "발화 내역 (화자 미구분)"}

```
{speaker_text}
```

---

## 📄 전체 원문 (STT 결과)

```
{combined_text}
```
"""

    output_path.write_text(md_content, encoding="utf-8")

    print(f"\n✅ 완료! ({elapsed_str})")
    print(f"   저장 위치: {output_path.resolve()}")


if __name__ == "__main__":
    main()
