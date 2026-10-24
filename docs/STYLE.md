# STYLE — Engine Routing & Visual Rules

## 1. Engine routing (per scene)

Break every video into modular scenes of 8–20 seconds. Unless the user explicitly requests an engine for the whole video or a scene, choose per scene:

**Use `"engine": "manim"` when the scene needs:**

- LaTeX formulas and step-by-step derivations (`TransformMatchingTex`).
- Probability distributions, density functions, areas under curves, 2D/3D axes, integrals, geometric proofs.
- Geometric algorithms, vectors, graphs, or continuous simulations (Monte Carlo, Markov chains, phyllotaxis spirals, physics).

**Use `"engine": "remotion"` when the scene needs:**

- High-impact hooks, kinetic typography, structured summary or call-to-action cards.
- Conceptual system diagrams (batteries, CPU architecture, network flows) with Lucide/SVG icons and Flexbox/Grid layouts.
- Comparison tables, timelines, UI mockups.

When a scene needs both (e.g. a UI card containing a formula), pick the engine for the dominant element and approximate the other: Remotion can render simple formulas as styled text; Manim can draw simple cards with `RoundedRectangle`. If both are essential, split it into two scenes.

## 2. Zero-seam rule

Both engines must look indistinguishable in the final edit. All values below come from `shared/theme.json`; never hardcode them.

- **Background:** `#0B0F19` in both engines (Manim `config.background_color`, Remotion root `backgroundColor`).
- **Palette:**

  | Role               | Color     |
  |--------------------|-----------|
  | Primary            | `#38BDF8` (Sky) |
  | Secondary          | `#A855F7` (Purple) |
  | Accent / Highlight | `#F59E0B` (Amber) |
  | Success            | `#10B981` (Emerald) |
  | Text               | `#F8FAFC` |
  | Text muted         | `#94A3B8` |
  | Surface (cards)    | `#131A2A` |
  | Border             | `#1E293B` |

- **Typography:** Inter for all text; JetBrains Mono for code, numbers in tables, and technical labels. Formulas use LaTeX's default math font (acceptable contrast with Inter, it reads as "math"). Use the type scale in `theme.json` per orientation; do not invent sizes.
- **Scene boundaries:** every scene starts on an empty background, fades elements in over `motion.scene_fade_in_sec`, and fades everything out during the final padding (`SyncedScene.finish()` / `<Fade>`). Cuts between scenes therefore always happen on a clean background, whichever engines meet.
- **Motion:** prefer smooth ease-in-out; avoid bounces and overshoot in one engine if the other cannot match them. Keep movements purposeful and in sync with cues.

## 3. Layout zones

Defined as fractions of the canvas in `theme.json → zones`:

- **Safe area:** everything stays within the central 85 % of the canvas.
- **Content zone:** where all visuals live.
- **Subtitle zone:** reserved band for subtitles. **Visuals never enter it, even when subtitles are off**, so a subtitled version can be produced later by `stitch.py` without re-rendering.
- **Vertical (9:16):** below the subtitle zone is covered by TikTok/Reels/Shorts UI (captions, buttons). Also keep important elements away from the right-hand edge, where platform buttons sit.

## 4. Text and language rules

- **No visible text or narration hardcoded in scene code.** Use `S("key")` (Manim) or `props.strings["key"]` (Remotion). Keys are namespaced by scene: `scene_02.title`, `scene_02.axis_x`.
- Words inside formulas (`\text{spam}`) also come from strings.
- In Manim, render words with `Text()` (Pango, supports any script), never with `Tex()`. Use `MathTex` only for mathematics. LaTeX does not handle non-Latin scripts (Chinese, Japanese, Arabic…) without extra configuration.
- Design for text expansion: translations can be 30 % longer (German, French). Give text boxes room, prefer wrapping and auto-fit (scale down, never below the `caption` size) over fixed widths.
- Numbers, units and formulas follow the target language's conventions when they appear as text (decimal comma vs point) — keep them in strings, not in code.

## 5. Timing rules

- Animations are anchored to **cues** from the narration, not to hardcoded seconds. Use `self.wait_until("cue")` / `self.until("cue")` in Manim and `useCue("cue")` in Remotion.
- Fixed durations are allowed only for short transitions (≤ 0.6 s) and the fade-in.
- Leave at least 0.3 s between consecutive cue-driven animations so translated narrations with slightly different spacing still fit.
