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
- **Scene boundaries:** every scene starts on an empty background, fades elements in over `motion.scene_fade_in_sec`, and fades everything out during the final padding (`SyncedScene.finish()` / `<Fade>`). Cuts between scenes therefore always happen on a clean background, whichever engines meet. The one exception is a camera transition between two scenes (section 6), which replaces the fades on the joined side and also cuts on a clean background.
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

## 6. Camera

The camera is for explaining, not for decoration. Every move must have a visual relation between what is on screen before and after it; without one, use no camera. Four tools:

- **Geometric zoom** (*push-in*): the camera moves closer inside the same space; what you see at the end was already on screen, only bigger. Its reverse, **opening on a detail and pulling back** (*reveal*), starts the scene on the detail and then shows where it sits.
- **Semantic zoom** (*zoom-through*): zooming in changes the level of detail or abstraction. What appears is not the object enlarged but another drawing of what is inside it (ball → molecules → atoms; population → one person → their coin toss; histogram → one bar → the cases in it). Three phases: dive into an element until the background closes in, switch representation on the clean background, let the new level emerge from the center. **Zooming out** is the same played backwards: the level shrinks into the center, and the camera pulls out of the element it was inside.
- **Lens**: a circle or a rounded rectangle with a magnified, live view of a small region, while the whole stays on screen, joined to its source by two lines.
- **Lateral transition**: the camera leaves one scene sideways until only background shows and arrives at the next scene moving the same way; it reads as one continuous move from one board to the next.

### Choosing (decide it when writing the script)

| What the narration does | Camera |
|---|---|
| Focuses on a detail too small at the default framing, and the rest does not matter for a while | Geometric zoom in, then back out |
| Focuses on a detail, but its place in the whole must stay visible | Lens |
| Starts from a detail, then shows the whole it belongs to | Open on the detail and pull back |
| Goes down a level (population → individual, system → component, bar → cases) | Semantic zoom in |
| Goes up a level (individual → population, atom → molecule) | Semantic zoom out |
| Moves to something at the same level (next case, second example, the other side of an equation) | Lateral transition between the two scenes |
| Moves from a concept to an example of it | If the example is a visible element of the concept (a point of the curve, one bar, one person): semantic zoom in onto it. If the example applies a formula or rule: no camera; keep the formula on screen, smaller and at the top, and work the example below it. If nothing visual links them: no camera (the normal cut), with the narration marking the change ("let's see an example") |
| Anything else: hooks, title and summary cards, text-heavy scenes, tables, formula derivations | No camera |

**Budget.** At most one camera move per scene (a zoom in and its zoom back count as one; so does a lens opening and closing), in at most about one scene out of three. At most two camera transitions between scenes (semantic or lateral) per minute of video; all other cuts use the normal fade. Do not repeat the same move in consecutive scenes. A 60-second vertical video usually needs one or two camera moves, or none.

**In the script (`docs/PRODUCTION.md`, Step 2):** write each move into the scene's `visual_plan` with its cue ("geometric zoom into the right tail at `tail`, back at `back`"; "ends with a lateral transition to the right into scene_04"). Place the cue right before the words that name what the move shows, and leave room after it: about 2 s for a zoom or a lens, 2.5 s for a semantic zoom (both halves). For a semantic join between scenes, let the sentence carry over the cut: the first scene ends naming what we enter ("let's look inside one person,"), the next begins with what is inside it.

### Timing

- Start each move at its cue and keep the camera still while the narration explains what it shows.
- Durations: geometric zoom 1–2 s; semantic zoom in 1.5–2 s, then emerge 0.6–0.9 s; semantic zoom out: recede 0.6–0.8 s, then 1.5–2 s; lens 0.6–1 s to open, 0.6–0.8 s to close. Never under 0.6 s: it reads as a jump. A lateral transition always takes `theme.json → camera.pan_sec` on each side of the cut, so that both scenes move at the same speed there; do not change it per scene.
- The easings are built in, the same in both engines.

### Rules

- **Content zone only.** With the camera, everything is clipped to the content zone, so zoomed content never enters the subtitle zone or the margins. Elements that should not move with the camera (level labels, scale bars) are pinned: `self.pin(mob)` in Manim, `<Camera pinned={…}>` in Remotion. Pinned elements fade out with everything else in a semantic zoom and travel with the content in a lateral transition, in both engines.
- **Name the levels** of a semantic zoom with a pinned label ("population", "individual") or, in physical zooms, a scale indicator ("1 m → 1 µm"). If there is a scale, its values must be correct.
- **Everything grows with the zoom,** text and line widths included, in both engines (the lens too). Labels that only appear while zoomed in must be drawn at their on-screen size divided by the zoom, and must still read at least at `caption` size on screen.
- **Semantic zoom targets are convex shapes** (circle, square, card): the zoom ends when the shape covers the content zone.
- **Lens:** plan room for it when laying out the scene (an empty part of the content zone, never over what the narration is talking about); it must not overlap its source. Choose the magnification so the detail fills most of the lens, between 2 and 4 (default `camera.lens_zoom`). If it would need more, the detail is too small for a lens: use a geometric zoom, or show its value as a label instead of magnifying it (a probability of 1/1024 is read as a number, not as a bar height). Use the lens at the default framing, not while zoomed in. **Shape:** a circle for a compact detail (a point, a tail, an intersection); a rectangle with the proportions of the detail for a long one (a line of fine print, a stretch of an axis, a subscript row of a table), so it is not cut at the ends. No other shapes.
- **Joining two scenes** (also between engines): the first ends with `zoom_through` / `zoomThrough` or `pan_out` / `panOut` on its last frame, and the next starts on its first frame with `emerge` / `<Emerge>` or `pan_in` / `panIn` (same direction). The cut falls on a clean background: the first frame of the next scene is background only (in a lateral transition the last frame of the first scene may still show an edge leaving, which keeps the motion continuous). Labels the next scene pins appear with it: fade them in alongside `emerge` (Manim), or animate their opacity over the `<Emerge>` frames (Remotion); with `pan_in` / `panIn` they arrive with the content. In Remotion, turn off the `<Fade>` on the joined side (`fadeIn={false}` / `fadeOut={false}`). Never try to match the last frame of one scene with the first of the next (*match cut*): it breaks easily, especially between engines.
- **Check every camera move frame by frame.** QA frames show composition and zones, not the move itself. Extract a strip of frames across each move from the preview clip (one every 0.1–0.15 s, from just before its cue to just after it ends; e.g. `ffmpeg -ss <start> -t <duration> -i <clip> -vf "fps=8,scale=360:-1,tile=8x3" -frames:v 1 strip.png`, which fits up to 3 s) and check, in order, that nothing jumps between consecutive frames, that what the move shows is readable at the end, and that nothing enters the subtitle zone.

### Manim

Inherit from `CameraScene` instead of `SyncedScene`. Most methods return animations for `self.play`:

```python
from studio.camera import CameraScene

class Scene03(CameraScene):
    scene_id = "scene_03"

    def construct(self):
        # … axes, curve, tail; level label pinned with self.pin(label)
        self.wait_until("tail")
        self.play(self.zoom_to(tail), run_time=self.until("back", gap=0.3, cap=2.0))
        self.wait_until("back")
        self.play(self.zoom_reset(), run_time=self.until("next", gap=0.3, cap=1.5))
        self.wait_until("next")
        self.play(self.zoom_through(bar), run_time=self.until("cases", gap=0.3, cap=2.0))
        # The scene is empty now and the camera is back at the default framing.
        self.play(self.emerge(cases), run_time=self.frames(0.6))
        self.wait_until("back_up")
        self.play(self.recede(), run_time=self.frames(0.7))
        self.pin(histogram_label)
        self.play(self.zoom_out_of(new_bar, histogram, histogram_label), run_time=self.frames(1.8))
        self.finish()
```

- `zoom_to(target, fill=…, zoom=…)`: frames a mobject so it fills `fill` of the content zone (default `theme.json → camera.fill`), or zooms by `zoom` (2 = twice as big) on a mobject or a point. Two `zoom_to` with the same `zoom` make a straight pan.
- `zoom_reset()`: back to the default framing.
- `start_at(target, fill=…, zoom=…)`: puts the camera on `target` without a move, before anything is shown; then `zoom_reset()` pulls back.
- `zoom_through(target)`: dives into `target` while everything fades to the background, then removes it all and resets the camera. `emerge(*mobjects)`: the next level grows from the center of the content zone.
- `recede()`: the current level shrinks into the center and fades out (pinned mobjects only fade). `zoom_out_of(target, *mobjects)`: the level above (`mobjects`, not in the scene yet) appears while the camera pulls out of `target`, one of them. Pin its labels with `pin` before.
- `pan_in(direction, *mobjects)` (plays it; use instead of `fade_in` at the start) and `pan_out(direction)` (plays it and ends the scene; use instead of `finish()`), with `LEFT`, `RIGHT`, `UP` or `DOWN`: where the camera travels.
- `lens(source, at, zoom=…, radius=…)` returns a round lens on the region around `source`, centered at `at` (points or mobjects); `lens(source, at, zoom=…, size=(width, height))` a rectangular one (size of the open lens: the detail's size times the zoom, plus a margin); show it with `self.play(self.open_lens(lens), …)` and hide it with `self.close_lens(lens)`.
- `pin(*mobjects)`: keeps mobjects fixed on screen; place them first.
- Move the camera only with these methods, never with `self.camera.frame.animate`. To fade out or clear everything mid-scene, use `self.content()` instead of `self.mobjects` (the mask that clips to the content zone is a mobject too).
- To end a scene on a semantic zoom that joins the next one: `self.play(self.zoom_through(target), run_time=self.until(self.total_sec))`, then `self.finish()`.

### Remotion

`<Camera>` goes inside `<SafeArea>` and lays its children out the same way. Moves start at a frame (usually a cue) and last a number of frames; `x`/`y` are the point of the content zone (fractions, 0–1) that ends at its center:

```tsx
import { Camera, Emerge, Lens, Recede, zoomOutOf, zoomReset, zoomThrough } from "@studio/Camera";

const moves = [
  { at: tail, frames: Math.min(90, back - tail - 18), x: 0.8, y: 0.75, zoom: 3 },
  zoomReset(back, 60),
  zoomThrough({ at: bar, frames: Math.min(120, cases - bar - 18), x: 0.3, y: 0.6, size: 120 }, props.orientation),
];

<SafeArea orientation={props.orientation}>
  <Camera orientation={props.orientation} moves={moves} pinned={/* first level label */}>{/* first level */}</Camera>
  <Emerge at={cases} frames={36}>{/* next level */}</Emerge>
</SafeArea>
```

- `initial={{ x, y, zoom }}` on `<Camera>`: the framing before its first move (open on a detail, then `zoomReset` to pull back).
- `zoomThrough` takes the size in px of the target's smaller side; after it ends, the `<Camera>` renders nothing, `pinned` included. `<Emerge at frames>` grows its children from the center of the content zone.
- Zooming out: wrap the current level in `<Recede at frames pinned={label}>`; the level above goes in another `<Camera>` whose first move is `zoomOutOf({ at, frames, x, y, size }, orientation)` (the element we come out of, as in `zoomThrough`); that `<Camera>` renders nothing before the move.
- Lateral transitions: `panIn(direction)` as the first move and `panOut(direction, props.timing)` as the last, with `"left" | "right" | "up" | "down"`; `<Fade fadeIn={false}>` / `fadeOut={false}` on that side.
- `<Lens orientation at frames until source center zoom radius>{same children as the Camera}</Lens>`, after the `<Camera>`: `source` and `center` in fractions of the content zone, `radius` in px; `size={{ w, h }}` (px) instead of `radius` makes it rectangular. It renders the children a second time, live.
- `pinned` is laid out over the content zone (`position: absolute` from its top left corner) and does not move with the camera. Something that must stay through a semantic zoom goes outside the `<Camera>`.
