# Minute Second Repository Map

`Minute-Second` is the gateway repository for the Minute Second project family. Product code and detailed docs live in the three public project repositories.

| Path | Public Repository | Role |
|---|---|---|
| `audio_extractor_stt/` | `https://github.com/geondongkim/Minute-Second-Audio-Extractor-STT` | Video upload, STT, diarization, AI meeting notes |
| `script-saver/` | `https://github.com/geondongkim/Minute-Second-Script-Saver` | Browser extension for meeting and lecture scripts |
| `lecture-slide-notes/` | `https://github.com/geondongkim/Minute-Second-Lecture-Slide-Notes` | Lecture video to slide PDF and NotebookLM Markdown |

## Root Repository Role

- Public landing page and README gateway.
- Submodule workspace for checking cross-project compatibility.
- Small orchestration scripts such as `tools/update-submodules.ps1`.
- No generated lecture outputs, videos, API keys, or local-only artifacts.

## Where Detailed Docs Live

- `audio_extractor_stt/docs/service-design.md`
- `script-saver/docs/extension-design.md`
- `lecture-slide-notes/docs/engine-design.md`
- Each project README has its own setup and validation commands.

## Submodule Workflow

```powershell
git clone --recurse-submodules https://github.com/geondongkim/Minute-Second.git
cd Minute-Second
git submodule update --init --recursive
.\tools\update-submodules.ps1
```

When editing product code, commit and push inside that submodule first. Then update this root repository only to record the new submodule pointer or landing-page text.