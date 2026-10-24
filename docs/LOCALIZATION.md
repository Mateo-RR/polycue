# LOCALIZATION — Languages, Voices & Subtitles for Existing Videos

An existing video is fully described by its manifest, scene code, locale files and timings. New versions reuse all of it: you change data, not visuals. Read `docs/STYLE.md` if you need to touch scene code.

## Cheap operations (what each change costs)

| Change requested                          | What to run                                        | Re-render scenes? |
|-------------------------------------------|----------------------------------------------------|-------------------|
| Add / remove subtitles                    | `stitch.py --subs burn\|soft\|none`                 | No |
| Change subtitle style                     | Edit `theme.json → subtitles`, then `stitch.py`     | No |
| Change voice, rate or pitch (same language) | Update `manifest.locales`, `tts_sync.py`, `render.py`, `stitch.py` | Yes (timing changes) — or use fit mode below |
| Fix a typo in narration only              | Edit narration, `tts_sync.py` (only that scene regenerates), `render.py --scenes`, `stitch.py` | Only that scene |
| Fix a typo in on-screen text              | Edit `strings.json`, `render.py --scenes`, `stitch.py` | Only that scene |
| New language                              | Full procedure below                               | Yes, automatically (no creative work) |
| Change orientation                        | Treat as a new production from Step 4 of `docs/PRODUCTION.md` | Yes, layouts must be reworked |

Why voice changes require a re-render: animations are synced to the narration. A different voice or language changes durations and cue times, so the visuals must be re-timed. Rendering is mechanical (same code, new timings), but it takes compute time.

## New language version

Input: an existing `slug`, a target language (resolve with `voices.json → aliases`), optional voice preferences, optional subtitles setting.

### 1. Register the locale

Add the target to `manifest.locales` with its voice settings (defaults from `voices.json`, or the user's preferences, as in `docs/PRODUCTION.md` Step 1).

### 2. Translate narration

Create `locales/<target>/narration.json` from the source language:

- Translate for the ear, naturally, not word by word. Keep the same meaning per scene.
- **Keep every `[[cue]]` marker, exactly once, in the same order**, placed before the word that carries the same meaning in the target language. Rephrase if needed so the order is preserved.
- Aim for similar length to the source (±15 %). If the target language tends to be longer, condense.
- Spell out formulas and symbols the way a native speaker would say them.

### 3. Translate on-screen strings

Create `locales/<target>/strings.json` with exactly the same keys as the source. Keep strings concise: they must fit the same boxes. Keep formulas, variable names and units unchanged unless the target convention differs (decimal comma, etc.).

### 4. Generate audio

```bash
manim_engine/.venv/bin/python scripts/tts_sync.py --slug <slug> --lang <target>
```

Optional **fit mode**: `--fit-to <source_lang>` adjusts speech rate (±15 % max) so each scene's duration matches the source. Use it when the user wants versions with identical timing, or to maximize reuse of `lang_neutral` scenes. Report any scene that could not be fitted.

### 5. Render

```bash
manim_engine/.venv/bin/python scripts/render.py --slug <slug> --lang <target> --preview
manim_engine/.venv/bin/python scripts/qa_frames.py --slug <slug> --lang <target> --preview --at-cues
```

Pay special attention in QA to text overflow (translations are often longer) and cue sync. Fix layout issues in scene code in a language-agnostic way (wrapping, auto-fit), never by special-casing one language, then re-render the affected scenes in **all** existing languages to keep them consistent.

Final render:

```bash
manim_engine/.venv/bin/python scripts/render.py --slug <slug> --lang <target> [--reuse-neutral-from <source_lang>]
```

### 6. Stitch

```bash
manim_engine/.venv/bin/python scripts/stitch.py --slug <slug> --lang <target> --subs <burn|soft|none>
```

Report output paths, the voice used, the fit-mode table if used, and any QA issues.

## Notes on scripts and fonts

- Inter and JetBrains Mono cover Latin, Greek and Cyrillic. For other scripts (Arabic, Hebrew, CJK, Devanagari…), add a fallback font family to `theme.json → fonts.fallback`, install it like in `docs/SETUP.md` Phase 1, and verify rendering in both engines and in burned subtitles before delivering.
- Right-to-left languages require layout review of every Remotion scene (`direction: rtl`) and of Manim text alignment. Warn the user that these versions need extra QA.
