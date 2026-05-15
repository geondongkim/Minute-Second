# AGENTS.md

This file gives Codex repository-wide guidance. Treat it as the project memory for coding style, commands, testing, and safety.

## Repository Overview

Minute_Second contains two user-facing tools:

- `audio_extractor_stt/`: FastAPI + React + WhisperX/Gemini service for extracting audio from videos, running STT/diarization, and generating meeting summaries.
- `script-saver/`: Chrome/Edge Manifest V3 extension for capturing meeting and lecture scripts, saving sessions, and generating AI summaries. Current adapters cover Microsoft Teams captions and Vimeo lecture captions.

Supporting documentation lives in `docs/`. Generated or local-only data lives in `results/`, `videos/`, `.venv/`, `ref/`, and API-key `.env` files.

## Operating Workflow

Use the same loop for non-trivial work: research the relevant files, plan the smallest safe change, implement, review the diff, then run the narrowest useful verification.

- Read existing code and docs before editing.
- Prefer existing project patterns over new abstractions.
- Keep changes scoped to the requested feature or bug.
- Do not edit generated assets, vendored libraries, `.venv/`, `results/`, `videos/`, or `ref/` unless the task explicitly requires it.
- Never commit secrets or real API keys. Keep `.env` files local.
- If Korean text appears garbled in PowerShell output, assume it is an encoding display issue and inspect the file with an editor or UTF-8-aware tooling before rewriting content.

## Commands

Backend service:

```powershell
cd audio_extractor_stt
uv sync
uv run uvicorn main:app --reload --port 8000
```

Frontend app:

```powershell
cd audio_extractor_stt/frontend
npm install
npm run dev
npm run lint
npm run build
```

Production-style single server:

```powershell
cd audio_extractor_stt/frontend
npm run build
cd ..
uv run uvicorn main:app --port 8000
```

CLI pipeline:

```powershell
cd audio_extractor_stt
uv run python run_cli.py "videos/meeting.mp4"
```

Chrome extension validation:

- Load `script-saver/` as an unpacked extension from `chrome://extensions/`.
- After editing extension files, reload the extension and test against Teams pages covered by `manifest.json`.

## Python Rules

- Target Python 3.10+.
- Use `uv` for dependency sync and command execution.
- Keep FastAPI routes, job state, and static-file serving in `main.py` consistent with the current structure.
- Keep FFmpeg concerns in `audio_extractor.py`, STT/diarization concerns in `stt_processor.py`, and LLM prompt/summary concerns in `summarizer.py`.
- Preserve CPU-friendly defaults unless the user asks for GPU-specific work.
- Treat `HF_TOKEN` as optional: diarization may be skipped, but transcription should still work when possible.

## Frontend Rules

- The React frontend uses TypeScript, Vite, React 19, ESLint, `react-markdown`, and `remark-gfm`.
- Keep API calls centralized in `audio_extractor_stt/frontend/src/api.ts`.
- Keep upload, progress, and result UI responsibilities in their existing components.
- Run `npm run lint` after TypeScript/React changes when dependencies are available.
- Run `npm run build` for user-facing UI changes when practical.

## Browser Extension Rules

- Maintain Manifest V3 compatibility and the permissions already declared in `script-saver/manifest.json`.
- Keep Teams DOM capture logic in `content_script.js`.
- Keep persistence/background coordination in `service_worker.js`.
- Keep popup/side panel behavior in `popup.js`, and detailed transcript/AI summary behavior in `viewer.js`.
- Do not add remote scripts. Extension pages must keep the current CSP-compatible local-script model.
- Be conservative with host permissions and storage schema changes.

## Documentation Rules

- Update `docs/` when changing setup, architecture, user flows, or externally visible behavior.
- Keep README and docs concise, command-focused, and current.
- Prefer UTF-8 text. Avoid rewriting Korean documentation unless the task is specifically about documentation or encoding cleanup.

## Verification Expectations

- For backend changes, run the smallest relevant `uv run ...` check or import/CLI smoke test.
- For frontend changes, run `npm run lint` and preferably `npm run build`.
- For extension changes, at minimum validate JSON syntax for `manifest.json` and reason through affected Chrome APIs; perform browser/manual testing when available.
- If a verification step cannot run because dependencies, network, FFmpeg, browser access, or credentials are missing, state that clearly in the final response.

## Git Hygiene

- Check `git status --short` before and after edits.
- Do not revert user changes.
- Keep commits focused if the user asks for commits.
