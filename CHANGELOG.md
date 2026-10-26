# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **CI** on GitHub Actions (`.github/workflows/ci.yml`): unit tests on Linux and Windows with Python 3.12 and 3.13, and a clean Linux install checked with `scripts/doctor.py` plus a Remotion typecheck.
- **Roadmap** section in the README.

## [0.1.0] — 2026-10-24

First public release.

### Added

- **Per-scene engine routing:** each scene of a video is rendered with Manim or Remotion (`docs/STYLE.md`), and both engines share one theme (`shared/theme.json`) so cuts between them are invisible.
- **Audio-first sync:** `scripts/tts_sync.py` generates the voiceover with `edge-tts`, aligns `[[cue]]` markers to word-boundary events and writes `timings.json`; scenes in both engines wait for cues, and clips are frame-exact.
- **Rendering and QA:** `scripts/render.py` (preview and final, frame-count verification) and `scripts/qa_frames.py` (keyframes with safe-area and subtitle-zone overlays for the agent's self-healing loop).
- **Stitching:** `scripts/stitch.py` normalizes both engines to BT.709, muxes the voice per scene, concatenates, applies two-pass loudness normalization (−14 LUFS / −1 dBTP) and produces word-timed subtitles (`.srt` / `.ass`, burned or soft).
- **Localization:** narration and on-screen text live in `locales/<lang>/`; `--fit-to` adjusts the speech rate of a translation so scenes keep the source duration. 11 languages preconfigured in `shared/voices.json`.
- **Agent spec:** `CLAUDE.md` and `docs/` (setup, style, production, localization) let Claude Code build the studio from scratch and produce a video from a one-line request; `docs/SETUP.md` also has a shortcut for an existing clone.
- **`scripts/doctor.py`:** checks system tools, fonts, the venv and `node_modules`, and prints how to fix what is missing on the current OS.
- **Example project:** `studio_showcase` (scene code and script; voiceover audio is regenerated, not versioned).
- Unit tests for narration parsing, cue alignment and subtitle layout.

### Known limitations

- Voiceover depends on `edge-tts`, an unofficial client for Microsoft's online TTS that could change or stop working.
- Tested on Windows 11 only.
- One engine per scene: a scene cannot mix Manim and Remotion layers.

[Unreleased]: https://github.com/Mateo-RR/polycue/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Mateo-RR/polycue/releases/tag/v0.1.0
