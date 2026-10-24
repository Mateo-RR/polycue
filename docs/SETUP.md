# SETUP — Build the Studio (one-time)

Goal: turn an empty repository (containing only `CLAUDE.md`, `docs/` and `shared/`) into a working studio, verified by an end-to-end smoke test. Work through the phases in order. Each phase ends with a check; do not move on until it passes.

General rules for this document:

- Detect the OS first (macOS, Linux, Windows/WSL) and adapt commands.
- **Ask the user before any system-level install** (`sudo`, `brew`, `winget`, `choco`, installers). Explain what will be installed and why. Project-local installs (`pip` in the venv, `npm` in `remotion_engine/`) need no confirmation.
- Pin dependency versions once installed (`requirements.txt` with `==`, `package.json` with exact versions) so the studio stays reproducible.
- If something fails, fix it and re-run that phase's check. Report anything you could not solve.

---

## Shortcut — the studio code already exists (e.g. a fresh clone)

If `scripts/`, `manim_engine/studio/` and `remotion_engine/package.json` already exist, the studio is already written: do **not** rebuild or overwrite it, and do **not** re-freeze dependency versions. Instead:

1. Run `python scripts/doctor.py` with the system Python (it needs no venv). Resolve everything it reports, following the rules of Phase 0 and Phase 1 step 3 (fonts), and asking before system-level installs.
2. Create the venv and install the pinned versions: `python -m venv manim_engine/.venv`, then `<venv python> -m pip install -r manim_engine/requirements.txt`.
3. In `remotion_engine/`: `npm ci`, then `npx remotion browser ensure`.
4. Re-run `scripts/doctor.py` until every check is `ok`.
5. Run Phase 2 (shared configuration and voices) and Phase 6 (smoke test), then create `.studio_ready` as Phase 6 describes.

If a script or helper turns out to be broken, fix that file in place instead of rewriting it from this document.

---

## Phase 0 — System prerequisites

If `scripts/doctor.py` exists, run it: it checks this table and prints how to fix each missing item for the current OS. Otherwise, check each tool and report what is missing:

| Tool                   | Check                         | Why                                       |
|------------------------|-------------------------------|-------------------------------------------|
| Python ≥ 3.12          | `python3 --version`           | Manim, scripts                            |
| Node.js ≥ 18           | `node --version`              | Remotion                                  |
| ffmpeg + ffprobe       | `ffmpeg -version`             | Normalizing, muxing, subtitles, QA frames |
| ffmpeg with libass     | `ffmpeg -filters \| grep ass` | Burned-in subtitles                       |
| LaTeX (`latex`, `dvisvgm`) | `latex --version`, `dvisvgm --version` | Manim `MathTex` / `Tex`          |
| Cairo + Pango (Linux)  | `pkg-config --exists cairo pangocairo` | Manim text rendering             |

Notes:

- LaTeX is the most common failure point. Prefer a full TeX distribution (TeX Live / MacTeX / MiKTeX). If the user wants a minimal one, follow the Manim CE installation docs for the required packages.
- On Linux, Manim also needs `libcairo2-dev`, `libpango1.0-dev` (or distro equivalents) to build.

**Check:** every tool in the table responds.

---

## Phase 1 — Folders and fonts

1. Create the folders from the layout in `CLAUDE.md` that do not exist yet: `scripts/`, `manim_engine/studio/`, `manim_engine/scenes/`, `remotion_engine/`, `projects/`, `output/`, `shared/fonts/`.
2. Download **Inter** and **JetBrains Mono** (static TTF files, at least Regular, Medium, SemiBold, Bold) from their official sources into `shared/fonts/`.
3. Install both families system-wide for the current user (Manim's `Text()` uses system fonts through Pango):
   - macOS: copy to `~/Library/Fonts/`
   - Linux: copy to `~/.local/share/fonts/` and run `fc-cache -f`
   - Windows: install per user (ask first)
4. Create a `.gitignore` excluding: `manim_engine/.venv/`, `remotion_engine/node_modules/`, `**/media/`, `projects/*/renders/`, `projects/*/qa/`, `output/`. Also keep videos private by default: ignore `projects/*`, `manim_engine/scenes/*` and `remotion_engine/src/videos/*/` (the user whitelists a video explicitly to publish it), and ignore `projects/*/locales/*/audio/` and `projects/*/locales/*/timings.json` so voiceover audio and its timings are never versioned.

**Check:** `fc-list | grep -i "Inter"` (or the OS equivalent) finds both families.

---

## Phase 2 — Validate shared configuration

1. Confirm `shared/theme.json` and `shared/voices.json` exist and parse as JSON.
2. Verify voices: run `edge-tts --list-voices` (after Phase 3 creates the venv) and compare with every voice in `shared/voices.json`. Remove voices that no longer exist, warn the user, and set `"verified": true` plus the date in `voices.json`.

**Check:** both files load; every listed voice exists.

---

## Phase 3 — Python engine (`manim_engine/`)

1. Create the venv: `python3 -m venv manim_engine/.venv`.
2. Install: `manim`, `edge-tts`, `mutagen`. Freeze exact versions to `manim_engine/requirements.txt`.
3. Create the helper package `manim_engine/studio/` with `__init__.py` and the three modules below.

### `studio/theme.py`

- Loads `shared/theme.json` (path resolved relative to the repo root, not the working directory).
- Exposes palette constants: `BG`, `PRIMARY`, `SECONDARY`, `ACCENT`, `SUCCESS`, `TEXT`, `TEXT_MUTED`, `SURFACE`, `BORDER`, and `FONT_SANS`, `FONT_MONO`.
- Function `configure()` that reads environment variables set by `scripts/render.py`:
  - `STUDIO_ORIENTATION` = `vertical` | `horizontal`
  - `STUDIO_QUALITY` = `preview` | `final`

  and sets on Manim's `config`: `background_color = BG`, `frame_rate` (final: 60, preview: 30), `pixel_width`/`pixel_height` (final: full canvas from theme; preview: half), and frame units so the aspect ratio matches:
  - horizontal: `frame_height = 8`, `frame_width = 8 * 16/9`
  - vertical: `frame_width = 8`, `frame_height = 8 * 16/9`
- Zone helpers that convert the fractions in `theme.json` (`safe_area`, `zones.<orientation>.content`, `zones.<orientation>.subtitles`) into Manim coordinates: `content_box()` returning `(left, right, top, bottom)` and `fit_in_content(mobject)` that scales a mobject down (never up) and centers it so it fits inside the content zone.
- `px_to_units(px)` for font sizes defined in pixels in `theme.json` → Manim `font_size`. Calibrate once: render a `Text` at a known `font_size`, measure its cap height in pixels, and store the factor.

### `studio/i18n.py`

- Reads `STUDIO_SLUG` and `STUDIO_LANG`, loads `projects/<slug>/locales/<lang>/strings.json`.
- `S(key)` returns the string; missing keys raise a clear error naming the key and the file.

### `studio/sync.py`

Base class `SyncedScene(Scene)` used by every Manim scene:

- Class attribute `scene_id = "scene_XX"`.
- In `setup()`: call `theme.configure()`, load `timings.json` for this scene (`duration_sec`, `total_sec = duration_sec + padding`, `cues`).
- `self.now()` → current scene time in seconds (`self.renderer.time`).
- `self.cue(name)` → time in seconds of a cue; unknown cue → clear error listing available cues.
- `self.wait_until(name_or_seconds)` → waits until that time; if already past it by more than one frame, log a warning (never wait a negative time).
- `self.until(name_or_seconds, min=0.2)` → seconds remaining until that point, for use as `run_time`.
- `self.finish()` → fades out everything during the padding (`motion.scene_fade_out_sec`) and waits exactly until `total_sec`. Raises if the scene already exceeded `total_sec` by more than one frame. Every scene's `construct()` must end with `self.finish()`.
- A scene begins on an empty background; the first elements fade in over `motion.scene_fade_in_sec`.

**Check:** a throwaway scene using `SyncedScene` with a fake `timings.json` renders in preview mode and lasts exactly `total_sec`.

---

## Phase 4 — Remotion engine (`remotion_engine/`)

1. Initialize a TypeScript Remotion project inside `remotion_engine/` non-interactively (do not use interactive scaffolders that block on prompts; create `package.json` and files directly if needed).
2. Install `remotion`, `@remotion/cli`, `react`, `react-dom`, `lucide-react`, `@remotion/google-fonts`, and Remotion's official Tailwind integration **matching the installed Remotion version** (check Remotion's docs for whether it is `@remotion/tailwind` or `@remotion/tailwind-v4`, and the matching `remotion.config.ts` override). Pin exact versions.
3. Run `npx remotion browser ensure` so the headless browser is available.
4. Create the helper modules in `src/studio/`:
   - `theme.ts`: imports `../../../shared/theme.json` (enable `resolveJsonModule`) and exports typed constants. Tailwind arbitrary values (`bg-[#0B0F19]`) are allowed only when they match theme values; prefer extending the Tailwind config from `theme.json`.
   - `fonts.ts`: loads Inter and JetBrains Mono via `@remotion/google-fonts` (weights used by the theme) and exports the font-family strings.
   - `useCue.ts`: hook `useCue(name)` returning the cue's frame from the `timing` prop; `useCueProgress(name, durationFrames)` returning 0→1 eased progress starting at that cue.
   - `SafeArea.tsx`: wrapper that lays children inside the content zone for the current orientation (from props). Optional `debug` prop draws the safe area and subtitle zone outlines.
   - `Fade.tsx`: scene-level wrapper applying the fade-in at start and fade-out during the final padding frames, so Remotion scenes cut exactly like Manim scenes.
   - `types.ts`: `SceneProps = { slug; lang; orientation; timing: SceneTiming; strings: Record<string,string> }`.
5. `src/videos/registry.ts`: exports an object `{ [slug]: { [sceneId]: Component } }`, built automatically with webpack's `require.context` from every `videos/<slug>/SceneNN.tsx` (which must export `SceneNN` → `scene_NN`). Nobody edits it by hand, so a clone that only contains some video folders still compiles.
6. `src/Root.tsx`: registers one `<Composition>` per registry entry with:
   - `id`: `${slug}--${sceneId}` with underscores replaced by hyphens (Remotion ids only allow letters, digits and hyphens).
   - `fps={60}` and `calculateMetadata` that sets `durationInFrames = props.timing.total_frames` and `width`/`height` from `props.orientation` and `theme.json`.
   - Sensible `defaultProps` so the Remotion Studio preview opens without crashing.
7. `src/index.ts`: `registerRoot(Root)`.

**Check:** `npx remotion compositions` lists the compositions without errors.

---

## Phase 5 — Scripts (`scripts/`)

All scripts: Python, run with the venv, `argparse` CLI, `--help` text, clear error messages, non-zero exit on failure, and paths resolved from the repo root.

### `scripts/doctor.py`

`doctor.py` (no arguments)

- Exception to the rule above: it must run with **any** Python 3 and only the standard library, because it is used before the venv exists.
- Checks every Phase 0 tool (with the minimum versions of the table; Cairo + Pango only on Linux), the theme fonts installed system-wide, the venv, every `==` pin of `manim_engine/requirements.txt` installed in the venv, and the Remotion version in `node_modules` against `package.json`.
- Prints a table (`ok` / `MISSING` + detail) and, for each failure, the fix command for the current OS (`winget`, `brew`, `apt`…). It never installs anything. Exits non-zero if any check fails.

### `scripts/tts_sync.py`

`tts_sync.py --slug <slug> --lang <lang> [--scenes scene_01 scene_03] [--fit-to <source_lang>] [--force]`

1. Load `manifest.json` and `locales/<lang>/narration.json`. Voice settings come from `manifest.locales[<lang>]` (voice, rate, pitch, volume), overridable per scene in `narration.json`.
2. Each narration may contain cue markers `[[cue_name]]` placed right before the word they refer to. Remove markers to get the clean text, remembering the index of the word that follows each marker.
3. Generate audio with `edge_tts.Communicate(text, voice, rate=…, pitch=…, volume=…)` streaming, requesting **word boundary** events (recent edge-tts versions default to sentence boundaries; pass `boundary="WordBoundary"` if the installed version supports it, and verify that events arrive). Write audio chunks to `locales/<lang>/audio/<scene_id>.mp3`; collect each word's offset and duration (units of 100 ns → seconds).
4. Measure real duration with `ffprobe` (fallback: `mutagen`).
5. Align cues: sequentially match normalized tokens (lowercase, no punctuation) of the clean text with boundary-event words; a cue's time is the start of its word. If alignment fails, fall back to a proportional estimate by character position and print a warning naming the cue.
6. Validate: every cue declared in `manifest.scenes[].cues` appears exactly once, in the declared order. Otherwise fail with a precise message.
7. Write `locales/<lang>/timings.json`:

```json
{
  "lang": "es-ES",
  "voice": "es-ES-AlvaroNeural",
  "fps": 60,
  "padding_frames": 24,
  "scenes": {
    "scene_01": {
      "audio": "audio/scene_01.mp3",
      "hash": "<sha256 of text+voice+rate+pitch+volume>",
      "duration_sec": 9.84,
      "duration_frames": 591,
      "total_frames": 615,
      "total_sec": 10.25,
      "cues": { "inbox": { "sec": 1.32, "frame": 79 } },
      "words": [ { "text": "Cada", "start": 0.05, "end": 0.31 } ]
    }
  }
}
```

   `duration_frames = ceil(duration_sec * 60)`, `total_frames = duration_frames + padding_frames`, `total_sec = total_frames / 60`.
8. Caching: skip a scene whose hash is unchanged unless `--force`.
9. `--fit-to <source_lang>`: for each scene, aim for the source language's `duration_sec`. Generate once, compute the ratio, adjust `rate` and regenerate (max 2 retries), clamped to ±15 % around the configured rate. Record the final rate in `timings.json` and print a table of target vs achieved durations.

### `scripts/render.py`

`render.py --slug <slug> --lang <lang> [--scenes …] [--preview]`

- Reads the manifest; for each scene, dispatches by `engine`.
- **Manim:** sets `STUDIO_SLUG`, `STUDIO_LANG`, `STUDIO_ORIENTATION`, `STUDIO_QUALITY`, runs `manim render manim_engine/scenes/<slug>/<scene_id>.py <ClassName>` with a temporary `--media_dir`, disables audio/sections, then moves the resulting mp4 to the destination.
- **Remotion:** writes a props JSON (`slug`, `lang`, `orientation`, `timing` for that scene, `strings`) and runs `npx remotion render <compositionId> <out> --props=<file> --codec=h264 --pixel-format=yuv420p` (preview: add `--scale=0.5`). Runs from `remotion_engine/`.
- Destinations: final → `projects/<slug>/renders/<lang>/<scene_id>.mp4`; preview → `projects/<slug>/renders/<lang>/preview/<scene_id>.mp4`.
- After each render, verify with `ffprobe`: frame count equals `total_frames` (final) or matches `total_sec` within one frame (preview). Print a summary table.
- Scenes marked `"lang_neutral": true` in the manifest may be rendered once in the source language and reused (see `docs/LOCALIZATION.md`); `render.py --reuse-neutral-from <source_lang>` copies them instead of rendering when their durations match within one frame.

### `scripts/qa_frames.py`

`qa_frames.py --slug <slug> --lang <lang> [--scenes …] [--preview] [--at-cues]`

- For each scene, extract PNGs at the middle and at `total_sec − 0.45 s` (just before the fade-out), plus one frame 0.5 s after each cue with `--at-cues`.
- Save two versions to `projects/<slug>/qa/<lang>/`: the plain frame and a copy with overlays drawn by ffmpeg `drawbox`: the 85 % safe area (one color) and the subtitle zone (another color).
- Print the list of generated files.

### `scripts/stitch.py`

`stitch.py --slug <slug> --lang <lang> [--subs burn|soft|none] [--preview]`

1. For each scene in manifest order, take the clean clip and its mp3, then:
   - video: scale/pad to the exact canvas, `fps=60`, `format=yuv420p`, trim or pad (`tpad=stop_mode=clone`) to exactly `total_frames`;
   - audio: resample to 48 kHz stereo, `apad`, trim to exactly `total_sec` (audio starts at 0 s of the scene; the padding is silence).
   Mux each scene into an intermediate file with identical codec parameters. Because each scene carries its own audio, drift across scenes is impossible.
2. Concatenate intermediates (concat demuxer; re-encode only if parameters differ).
3. Normalize loudness to −14 LUFS integrated, −1 dBTP (`loudnorm`, two-pass).
4. Subtitles (always generate the files, even with `--subs none`):
   - Global word times = scene start offset + word times from `timings.json`.
   - Group words into cues following `theme.json → subtitles` (max chars per line, max lines, min duration); break at punctuation when possible.
   - Write `projects/<slug>/subtitles/<lang>.srt` and `<lang>.ass`. The `.ass` style uses the theme font, size, colors and outline, with its vertical position inside the subtitle zone for the orientation.
   - `burn`: apply the `.ass` with ffmpeg's `ass` filter using `fontsdir=shared/fonts`.
   - `soft`: add the `.srt` as a `mov_text` track with the correct language tag.
5. Outputs in `output/<slug>/`:
   - `<slug>_<lang>.mp4` (no subtitles, or soft subtitles)
   - `<slug>_<lang>_subs.mp4` (burned subtitles, when `burn`)
   - `<slug>_<lang>.srt` (always)
6. Verify with `ffprobe`: duration equals the sum of `total_sec` (± one frame), 1 video + 1 audio stream, correct resolution/fps. Print the final paths.

**Check:** every script prints `--help` correctly.

---

## Phase 6 — Smoke test (end to end)

Create `projects/_smoke_test/` with:

- `manifest.json`: `orientation: "vertical"`, source language `es-ES`, two scenes of ~4 s: `scene_01` (Remotion: a title card plus one Lucide icon) and `scene_02` (Manim: `MathTex` of `a^2 + b^2 = c^2` that transforms into `c = \sqrt{a^2 + b^2}`), each with one cue.
- `locales/es-ES/narration.json` and `strings.json` with short Spanish text.

Then run the full pipeline: `tts_sync.py` → `render.py --preview` → `qa_frames.py --preview` (inspect the images) → `render.py` → `stitch.py --subs burn`.

Repeat `tts_sync.py` + `render.py` + `stitch.py` for `en-US` (translate the two narrations and strings) to prove localization works.

**Check (all must pass):**

- [ ] Final videos exist for `es-ES` and `en-US`, 1080x1920, 60 fps, yuv420p, with audio.
- [ ] Durations equal the sums of `total_sec`.
- [ ] Background color in both engines samples as `#0B0F19` (extract one pixel per scene with ffmpeg and compare).
- [ ] Inter renders in both engines (visual check in QA frames).
- [ ] Burned subtitles appear inside the subtitle zone and are readable.
- [ ] Cue timing is visibly in sync with the voice.

When everything passes, create `.studio_ready` at the repo root (a per-machine marker, git-ignored) containing the date and the pinned versions of Manim, Remotion, edge-tts and ffmpeg. Keep `projects/_smoke_test/` as a reference example. Report to the user what was installed and any warnings.
