# PolyCue Studio

**Ask for an explainer video in one sentence. A coding agent writes the script, records the voiceover, builds each scene in Manim or Remotion, checks the frames and hands you a finished, subtitled MP4, in the language you ask for.**


[![PolyCue Studio demo: pipeline overview (Remotion) and feature grid (Manim)](docs/assets/demo.gif)](https://github.com/user-attachments/assets/ee653de6-6681-4f15-bee3-d4e448b07062)


*The demo above was produced by the studio itself, with no manual editing. Its source is included in the repo as an example ([`studio_showcase`](#example-project)).*

## What it does

- **Two engines, one video.** Each scene is rendered with the engine that suits it: [Manim](https://www.manim.community/) for math, formulas and simulations; [Remotion](https://www.remotion.dev/) for kinetic typography, diagrams and UI. The cuts between them are invisible.
- **Audio first.** The voiceover is generated before any animation, and every animation waits for a cue word in the narration, so visuals stay in sync with the voice to the frame.
- **Cheap translations.** Scene code contains no text: narration and on-screen strings live in per-language files. A new language is a translation plus a mechanical re-render, and the voice speed can be adjusted so each scene keeps its original length. Scenes without text are rendered once and reused in every language.
- **Cheap edits.** Changing a finished video only redoes what changed: fixing a sentence regenerates the voice and render of that scene alone, and the agent follows a cost table (`docs/LOCALIZATION.md`) to pick the cheapest way to apply each change.
- **Subtitles without re-rendering.** Word-timed subtitles, burned in or as a separate track. A subtitle zone is always kept clear, so you can add them at any time.
- **Self-checking.** The agent extracts keyframes with safe-area overlays, inspects them and fixes broken layouts before the final render.
- **Vertical or horizontal**, for Shorts/Reels/TikTok or YouTube.

The repo is written as an **executable spec** for [Claude Code](https://claude.com/claude-code): `CLAUDE.md` and `docs/` describe how to build the studio from scratch and how to produce a video, and the agent follows them.

## Quickstart

**Requirements:** Python ≥ 3.12, Node ≥ 18, ffmpeg with libass, and a LaTeX distribution (for Manim's formulas). On Linux, also Cairo + Pango. Check everything at once with:

```bash
python scripts/doctor.py   # lists what is missing and how to install it on your OS
```

### With Claude Code (intended workflow)

```bash
git clone https://github.com/Mateo-RR/polycue.git && cd polycue
claude
> Set up the studio            # installs the pinned dependencies and runs an end-to-end smoke test
> Make a 60-second video about Bayes' theorem for YouTube
> Now make a Spanish version
```

### Manual

The scripts also work without the agent, for a project whose script and scenes are already written (like the included example):

```bash
PY=manim_engine/.venv/bin/python        # Windows: manim_engine\.venv\Scripts\python
$PY scripts/tts_sync.py  --slug studio_showcase --lang en-US                  # voiceover + timings
$PY scripts/render.py    --slug studio_showcase --lang en-US --preview        # fast preview
$PY scripts/qa_frames.py --slug studio_showcase --lang en-US --preview --at-cues
$PY scripts/render.py    --slug studio_showcase --lang en-US                  # final render
$PY scripts/stitch.py    --slug studio_showcase --lang en-US --subs burn      # → output/studio_showcase/
```

Set up the environment first by following `docs/SETUP.md` (section "Shortcut").

## How it works

```text
narration.json ──► tts_sync.py ──► audio/*.mp3 + timings.json (durations, cue frames, word times)
                                          │
manifest.json (engine per scene) ──► render.py ──► Manim clips ─┐
                                          │       Remotion clips ┤  clean: no audio, no subtitles
                                          ▼                      │
                                   qa_frames.py (agent QA loop)  │
                                                                 ▼
                         stitch.py: normalize + mux voice + concat + loudnorm + subtitles ──► output/<slug>/*.mp4
```

### Why not just use manim-voiceover or Remotion's agent skills?

The building blocks already exist, and this project uses them where they fit. [`manim-voiceover`](https://pypi.org/project/manim-voiceover/) syncs narration inside Manim, and Remotion ships [agent skills](https://github.com/remotion-dev/skills) for Claude Code. Each of them stays inside its own engine. What this repo adds is the layer that makes the two engines work as one production pipeline:

| Problem | How it is solved here |
|---|---|
| Two engines must look like one | A single `shared/theme.json` drives Manim, Remotion **and** the subtitle renderer. Every scene starts and ends on a clean background. `stitch.py` re-encodes both engines' BT.601 output to tagged BT.709, so colors match when one engine cuts to the other. |
| Animations drift from the voice | `tts_sync.py` reads word-boundary events from the TTS to find each `[[cue]]` marker in the narration. Scenes wait for cues, not for hard-coded seconds. `SyncedScene` compensates for Manim's frame rounding, so every clip is **frame-exact**, and `render.py` / `stitch.py` verify frame counts. |
| Translations usually mean re-doing the video | Strings and narration live in `locales/<lang>/`. `--fit-to <lang>` adjusts the speech rate of a translated voice (±15 %) so each scene keeps the source duration. Narration is hashed per scene, so only changed scenes hit the TTS. |
| Subtitles are an afterthought | Word-timed, balanced two-line cues, exported as `.srt`/`.ass` (burned or soft). The ASS font size is corrected with the font's OS/2 metrics, so libass matches the CSS size. |
| Agents produce broken layouts | `qa_frames.py` extracts keyframes at every cue, with safe-area and subtitle-zone overlays. The agent fixes scenes in a bounded loop (max. 3 iterations per scene, `docs/PRODUCTION.md` step 5). |
| Final mix is uneven | Two-pass EBU R128 loudness normalization (−14 LUFS / −1 dBTP), with audio trimmed to the exact video length. |

## Repository layout

| Path | What lives there |
|---|---|
| `CLAUDE.md`, `docs/` | The agent-facing spec: setup, engine routing and visual rules, production and localization procedures |
| `shared/` | `theme.json` (colors, fonts, canvas, zones, subtitle style), `voices.json`, fonts |
| `scripts/` | `doctor.py`, `tts_sync.py`, `render.py`, `qa_frames.py`, `stitch.py` |
| `manim_engine/studio/` | `SyncedScene` (cue-based timing), theme and i18n helpers |
| `remotion_engine/src/studio/` | `useCue`, `SafeArea`, `Fade`, theme bridge |
| `projects/<slug>/` | Per video: language-neutral `manifest.json` + `locales/<lang>/` (narration, strings) |
| `manim_engine/scenes/<slug>/`, `remotion_engine/src/videos/<slug>/` | Per video: scene code for each engine |
| `tests/` | Unit tests for narration parsing, cue alignment and subtitle layout |

### Example project

`studio_showcase` (the demo video) is the only video included: 2 scenes, one per engine. Its voiceover audio is not included; `tts_sync.py` regenerates it. Your own videos are git-ignored by default, so they stay local unless you whitelist them in `.gitignore`.

### Tests

```bash
$PY -m pip install -r requirements-dev.txt
$PY -m pytest tests
```

## Status and limitations

See the [changelog](CHANGELOG.md) for what each version includes.

- **Tested on Windows 11.** The setup also covers macOS and Linux, but those have not been tested yet.
- **Voiceover** uses [`edge-tts`](https://github.com/rany2/edge-tts), an unofficial client for Microsoft Edge's online TTS. It is free and sounds good, but it needs a network connection and could change or stop working without notice.
- **Languages:** 11 are preconfigured in `shared/voices.json` (Spanish, English, French, German, Italian, Portuguese, Galician, Catalan, with regional variants). Any other language with an edge-tts voice can be added, as long as its on-screen text uses Latin or Greek script, which the theme fonts cover.
- **The agent writes the scenes.** The scripts work on their own, but nothing generates scene code without the agent.
- **One engine per scene.** A scene cannot mix Manim and Remotion layers; a scene that needs both is split in two.

## Authorship

I designed the architecture, the rules and the agent spec (`CLAUDE.md`, `docs/`). The implementation and the example videos were produced by Claude Code following that spec, then reviewed and iterated.

## License

Code in this repository: [MIT](LICENSE). Fonts in `shared/fonts/` keep their own licenses (Inter and JetBrains Mono, both SIL OFL 1.1).

Third-party tools are **not** covered by the MIT license and have their own terms. As of October 2026:

- **Remotion** is source-available, not open source. It is free for individuals and small teams; larger companies need a company license. See [remotion.dev/license](https://remotion.dev/license).
- **Voiceover** uses [`edge-tts`](https://github.com/rany2/edge-tts) (LGPLv3), an unofficial client for Microsoft Edge's online read-aloud service. The generated audio is subject to Microsoft's terms. For commercial use, consider the official [Azure AI Speech](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services) service, which offers the same voices.

This information may become outdated, and it is not legal advice. Check each project's current terms before relying on it. You are responsible for complying with the terms of the tools and voice providers you use, and for having the rights to any voice you use or clone.
