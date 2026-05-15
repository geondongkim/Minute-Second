---
name: lecture-slide-notes
description: Use when the user wants to turn Vimeo, YouTube, course-page, or local lecture videos into slide PNGs, searchable PDFs, OCR text, or NotebookLM-friendly Markdown. Prefer the local CLI/MCP tools over browser-only processing for Vimeo/YouTube, HLS, OCR, and high-resolution PDF workflows.
---

# Lecture Slide Notes Skill

Use the `lecture-slide-notes` project for lecture video processing tasks.

## Workflow

1. Resolve the input as one of: local video file, Vimeo player URL, YouTube URL, course lesson page URL, direct manifest URL, or capture JSON.
2. Prefer `https://player.vimeo.com/video/<id>` plus the lesson page referer for Vimeo downloads.
3. Use browser cookies only through local options such as `--cookies-from-browser`; do not ask the user to paste passwords.
4. Run `lecture-slide-notes doctor` before a long batch if the environment is unknown.
5. For a local video, run `lecture-slide-notes process-video <video> --output <output-dir>`.
6. For a Vimeo/YouTube/course URL, run `lecture-slide-notes process-url <url> --referer <lesson-url> --output-root <outputs>`.
7. For NotebookLM output, preserve the generated Markdown and searchable PDF together.

## Safety Boundaries

- Do not attempt to process DRM-protected streams.
- Do not exfiltrate cookies, API keys, or downloaded lecture files.
- Use the user's existing local access and keep generated files local unless the user explicitly asks otherwise.
