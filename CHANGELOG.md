# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-10-27

### Changed

- **Breaking: each video lives in a single folder.** Scene code moved from `manim_engine/scenes/<slug>/` and `remotion_engine/src/videos/<slug>/` to `projects/<slug>/scenes/manim/` and `projects/<slug>/scenes/remotion/`, and final videos from `output/<slug>/` to `projects/<slug>/output/`. Publishing a video now takes one `!projects/<slug>/` line in `.gitignore`.
- Remotion scenes import the studio helpers as `@studio/…` instead of `../../studio/…`; Manim scenes import their helpers as `from common import …` instead of `from scenes.<slug>.common import …`.
- `remotion_engine/src/videos/registry.ts` moved to `remotion_engine/src/registry.ts`.
- Remotion finds scene code outside its folder: `remotion.config.ts` adds the `@studio` alias and `remotion_engine/node_modules` to webpack, and writes `remotion_engine/src/sources.generated.css` (git-ignored) with one Tailwind `@source` per video, because Tailwind skips git-ignored folders and videos are git-ignored by default.
- Remotion Studio no longer rebuilds when renders, QA frames or outputs are written, and a video created while it is open gets its Tailwind classes without restarting it.

### Added

- **Parallel rendering:** `render.py --jobs N` (default: half the CPU threads). Manim scenes render in parallel; Remotion scenes run one at a time alongside them, since a single Remotion render already uses several cores. On a 58-second test video with 6 scenes (4 Manim, 2 Remotion), `--jobs 4` made rendering 2.1–2.3× faster and the whole pipeline 1.7–1.8× faster than one scene at a time, with the same output frame for frame (laptop with an Intel Core i7-10750H, 6 cores, in its Turbo and silent power modes; details and the reasons it is not 4× in the README).
- `scripts/benchmark.py` times the whole pipeline of a video with different `--jobs` values and checks that every run produces the same video.
- Two more example videos: `monte_carlo_pi` (the benchmark video, published so anyone can reproduce the numbers with `scripts/benchmark.py`) and `parallel_benchmark` (the benchmark results animation shown in the README).
- Remotion is bundled once per `render.py` run and every Remotion scene renders from that bundle.
- A failing scene no longer stops the others: `render.py` finishes the rest and reports every error after the summary table.
- `scripts/migrate_layout.py` moves videos from the 0.1 layout and rewrites their imports (`--dry-run` to preview).

### Upgrading from 0.1

Run `manim_engine/.venv/bin/python scripts/migrate_layout.py --dry-run`, then without `--dry-run` (on Windows, `manim_engine\.venv\Scripts\python`). If you had whitelisted videos in `.gitignore`, replace their old lines with one `!projects/<slug>/` line per video, as the script reminds you.

## [0.1.1] — 2026-10-26

### Added

- **CI** on GitHub Actions (`.github/workflows/ci.yml`): unit tests on Linux and Windows with Python 3.12 and 3.13, and a clean Linux install checked with `scripts/doctor.py` plus a Remotion typecheck.
- **Roadmap** section in the README.

### Changed

- README: the platform status now says what CI checks on Linux.

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

[0.2.0]: https://github.com/Mateo-RR/polycue/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/Mateo-RR/polycue/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Mateo-RR/polycue/releases/tag/v0.1.0
