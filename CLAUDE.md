# PolyCue Studio — hybrid AI video studio (Manim + Remotion)

You are an autonomous technical video producer. You build and operate a pipeline that combines **Manim Community Edition (Python)** and **Remotion (React/TypeScript + Tailwind)** in a single video, choosing the engine **per scene**, with voiceover from `edge-tts`, optional subtitles, and multi-language versions of the same video.

This file is an index. Read only the documents the current task needs.

## What to read for each task

| The user wants to…                                              | Read                                   |
|-----------------------------------------------------------------|----------------------------------------|
| Set up the studio (first time, or anything is missing/broken)   | `docs/SETUP.md`                        |
| Create a new video                                              | `docs/STYLE.md` → `docs/PRODUCTION.md` |
| Make a version of an existing video in another language         | `docs/LOCALIZATION.md`                 |
| Change voice, speed or subtitles of an existing video           | `docs/LOCALIZATION.md` (section "Cheap operations") |
| Fix or tweak a scene of an existing video                       | `docs/STYLE.md` → `docs/PRODUCTION.md` (steps 4–7 only) |

## Before any video task: environment check

1. If `scripts/`, `manim_engine/.venv/` or `remotion_engine/node_modules/` do not exist, or `.studio_ready` is missing at the repo root, the studio is not built yet. Tell the user, then follow `docs/SETUP.md` before doing anything else.
2. Never improvise a missing script inline. If a script described in `docs/SETUP.md` is missing or broken, fix the script itself so the next video benefits.
3. If `manim_engine/scenes/`, `remotion_engine/src/videos/` or `output/` still hold videos, they use the 0.1 layout. Tell the user and offer to run `scripts/migrate_layout.py` (try `--dry-run` first), which moves them into `projects/<slug>/`.

## Non-negotiable rules (summary)

- **Single source of truth:** colors, fonts, canvas sizes, safe areas and subtitle style live in `shared/theme.json`. Voices live in `shared/voices.json`. Never hardcode these values in scene code.
- **No hardcoded language:** scene code never contains visible text or narration. Visible text comes from `locales/<lang>/strings.json`; narration from `locales/<lang>/narration.json`. This is what makes translations cheap.
- **Audio first:** scene durations and animation timings come from the generated voiceover (`timings.json`), never from guesses.
- **Clean renders:** scene renders never contain audio or subtitles. Voice and subtitles are layered on only in `scripts/stitch.py`.
- **Subtitle zone is always reserved:** visuals never enter the subtitle zone defined in `theme.json`, even when subtitles are off, so subtitles can be added later without re-rendering.
- **Run all Python scripts with** `manim_engine/.venv` (e.g. `manim_engine/.venv/bin/python scripts/tts_sync.py …`; on Windows `manim_engine\.venv\Scripts\python`). The only exception is `scripts/doctor.py`, which runs with any Python 3 so it works before the venv exists.

## Repository layout

```text
.
├── CLAUDE.md                     # This index
├── .studio_ready                 # Created by SETUP when the smoke test passes
├── docs/
│   ├── SETUP.md                  # Build the studio (one-time)
│   ├── STYLE.md                  # Engine routing + visual rules
│   ├── PRODUCTION.md             # Pipeline for a new video
│   └── LOCALIZATION.md           # New language / voice / subtitle versions
├── shared/
│   ├── theme.json                # Colors, fonts, canvas, zones, subtitle style
│   ├── voices.json               # Voices per language + aliases
│   └── fonts/                    # Inter + JetBrains Mono (TTF), used by Manim and ffmpeg/libass
├── scripts/
│   ├── doctor.py                 # Checks system tools, fonts, venv and node_modules; prints fixes
│   ├── tts_sync.py               # Narration → mp3 + timings.json (durations, cues, words)
│   ├── render.py                 # Renders scenes with the right engine, in parallel (preview/final)
│   ├── qa_frames.py              # Extracts QA keyframes with safe-area overlay
│   ├── stitch.py                 # Normalize + mux audio + concat + subtitles → final mp4
│   └── migrate_layout.py         # One-off: moves videos from the 0.1 layout into projects/<slug>/
├── manim_engine/
│   ├── .venv/
│   ├── requirements.txt
│   └── studio/                   # theme.py, sync.py, i18n.py (shared helpers)
├── remotion_engine/
│   └── src/
│       ├── studio/               # theme.ts, useCue.ts, SafeArea.tsx, Fade.tsx (imported as @studio/…)
│       ├── registry.ts           # Finds projects/*/scenes/remotion/SceneXX.tsx
│       ├── Root.tsx
│       └── index.ts
├── projects/<slug>/              # Everything about one video lives here
│   ├── manifest.json             # Language-neutral: scenes, engines, cues, visual plans
│   ├── scenes/
│   │   ├── manim/scene_XX.py     # + helpers shared by the video's scenes (e.g. common.py)
│   │   └── remotion/SceneXX.tsx  # + helpers (e.g. ui.tsx)
│   ├── locales/<lang>/
│   │   ├── narration.json
│   │   ├── strings.json
│   │   ├── timings.json          # Generated by tts_sync.py
│   │   └── audio/scene_XX.mp3
│   ├── renders/<lang>/           # Clean scene clips (final) + preview/
│   ├── qa/<lang>/                # QA keyframes
│   ├── subtitles/<lang>.srt|.ass
│   └── output/                   # Final deliverables
```
