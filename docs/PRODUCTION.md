# PRODUCTION — Create a New Video

Prerequisite: the studio is built (`.studio_ready` exists). Read `docs/STYLE.md` first.

Execute the steps in order without stopping, unless the user asked to review the script first ("quiero revisar el guion", "show me the script first"): in that case pause after Step 2 and continue on approval.

---

## Step 1 — Parse the request

Extract these parameters. When the user does not specify one, use the default and state your assumptions in one line at the start of your report.

| Parameter     | Default                                  | Notes |
|---------------|------------------------------------------|-------|
| `slug`        | derived from topic, `snake_case`, ASCII  | Must be unique in `projects/` |
| `orientation` | `vertical`                               | "TikTok/Reels/Shorts" → vertical; "YouTube" → horizontal |
| Duration      | 60 s                                     | Total target; scenes of 8–20 s |
| Language      | `es-ES`                                  | Resolve names via `voices.json → aliases` ("inglés" → `en-US`) |
| Voice         | `voices.json → languages.<lang>.default` | "voz femenina/masculina" → first of `female`/`male` list; a specific name if given |
| Rate / pitch  | `voices.json → defaults`                 | "más rápido" → `+10%`, "mucho más rápido" → `+20%`, "más lento" → `-10%`; "más grave" → `-5Hz`, "más aguda" → `+5Hz` |
| Subtitles     | vertical: `burn`; horizontal: `none`     | User can ask for `burn`, `soft` or `none`. An `.srt` is always produced |
| Extra languages | none                                   | If the user asks for several languages up front, produce the source first, then follow `docs/LOCALIZATION.md` for each |

## Step 2 — Write the script

Create `projects/<slug>/manifest.json` (language-neutral):

```json
{
  "slug": "bayes_spam",
  "title": "Bayes y el filtro de spam",
  "orientation": "vertical",
  "fps": 60,
  "source_lang": "es-ES",
  "subtitles": "burn",
  "locales": {
    "es-ES": { "voice": "es-ES-AlvaroNeural", "rate": "+0%", "pitch": "+0Hz", "volume": "+0%" }
  },
  "scenes": [
    {
      "id": "scene_01",
      "engine": "remotion",
      "entry": "Scene01",
      "visual_plan": "Inbox UI; emails fall into a red spam folder; big kinetic title",
      "cues": ["inbox", "spam_folder"],
      "lang_neutral": false
    },
    {
      "id": "scene_02",
      "engine": "manim",
      "entry": "Scene02",
      "visual_plan": "Bayes theorem derivation with TransformMatchingTex; unit square split into proportional areas",
      "cues": ["formula", "denominator", "square"],
      "lang_neutral": false
    }
  ]
}
```

- `entry`: Manim class name or Remotion component name.
- `cues`: ordered list of sync points used by the scene's animations.
- `lang_neutral`: `true` only if the scene shows no text at all and has no cues; such scenes can be reused across languages.
- **Camera:** decide now, scene by scene, whether the camera helps (`docs/STYLE.md`, section 6: the table of what the narration does, and the budget). Most scenes need none. When one does, write the move and its cue into `visual_plan`, and write the narration so the cue falls right before the words that name what the move shows. Joins between scenes (semantic zoom or lateral transition) are planned here too, with the sentence carrying over the cut.

Create `projects/<slug>/locales/<lang>/narration.json`:

```json
{
  "scene_01": {
    "text": "Cada día llegan [[inbox]] miles de millones de correos a nuestras bandejas, y casi la mitad acaban [[spam_folder]] directamente en la carpeta de spam."
  },
  "scene_02": {
    "text": "Para entenderlo necesitamos [[formula]] el teorema de Bayes. La clave está [[denominator]] en el denominador, que podemos ver [[square]] como un cuadrado dividido en áreas.",
    "voice": null
  }
}
```

- Place `[[cue]]` right before the word where the animation should start. Every cue in the manifest appears exactly once, in order.
- Optional per-scene `voice`, `rate`, `pitch` override the locale defaults (e.g. a second narrator).
- Word budget: roughly 2.5 words per second at default rate. A 12 s scene ≈ 30 words.
- Write for the ear: short sentences, no parentheses, no symbols the voice cannot read. Spell out formulas in words ("P de A dado B").

Create `projects/<slug>/locales/<lang>/strings.json` with every visible text, keys namespaced by scene:

```json
{
  "scene_01.title": "¿Por qué tu correo sabe qué es spam?",
  "scene_01.folder": "Spam",
  "scene_02.text_spam": "spam",
  "scene_02.label_area": "P(B)"
}
```

## Step 3 — Audio first

```bash
manim_engine/.venv/bin/python scripts/tts_sync.py --slug <slug> --lang <lang>
```

Read `locales/<lang>/timings.json`. If a scene's `duration_sec` falls outside 8–20 s, or the total deviates more than 15 % from the target duration, edit the narration and re-run (only changed scenes regenerate).

## Step 4 — Generate scene code

Every scene animation lasts exactly `total_sec` (= audio duration + 0.4 s padding = `duration_frames + 24` frames). The helpers enforce this; do not compute it by hand.

**Manim** — `projects/<slug>/scenes/manim/<scene_id>.py`. Helpers shared by several scenes go in the same folder (e.g. `common.py`) and are imported as `from common import …`; do not name them like a standard-library or Manim module:

```python
from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

class Scene02(SyncedScene):
    scene_id = "scene_02"

    def construct(self):
        self.wait_until("formula")
        eq = MathTex(r"P(A \mid B)", "=", r"\frac{P(B \mid A)\,P(A)}{P(B)}", color=TEXT)
        fit_in_content(eq)
        self.play(Write(eq), run_time=self.until("denominator", min=0.6))
        # …
        self.finish()
```

**Remotion** — `projects/<slug>/scenes/remotion/<Entry>.tsx`, where `<Entry>` is `SceneNN` for `scene_NN` and the file exports a component with that same name. `remotion_engine/src/registry.ts` discovers it automatically; do not register it by hand. Import the studio helpers through the `@studio` alias, and local helpers (e.g. `./ui`) relatively:

```tsx
import { AbsoluteFill, Sequence } from "remotion";
import { SceneProps } from "@studio/types";
import { SafeArea } from "@studio/SafeArea";
import { Fade } from "@studio/Fade";
import { useCue } from "@studio/useCue";

export const Scene01: React.FC<SceneProps> = (props) => {
  const inbox = useCue("inbox", props.timing);
  const spam = useCue("spam_folder", props.timing);
  return (
    <Fade timing={props.timing}>
      <SafeArea orientation={props.orientation}>
        <Sequence from={inbox}>{/* inbox cards */}</Sequence>
        <Sequence from={spam}>{/* spam folder */}</Sequence>
      </SafeArea>
    </Fade>
  );
};
```

Follow every rule in `docs/STYLE.md` (no hardcoded text, theme values only, content zone only).

**Camera moves** planned in `visual_plan` (zoom, semantic zoom, lens, lateral transition): Manim scenes inherit from `CameraScene` instead of `SyncedScene`; Remotion scenes wrap their content in `<Camera>`. Rules and the full API: `docs/STYLE.md`, section 6. Do not add moves the plan does not have.

## Step 5 — Preview render + visual QA (self-healing loop)

```bash
manim_engine/.venv/bin/python scripts/render.py --slug <slug> --lang <lang> --preview
manim_engine/.venv/bin/python scripts/qa_frames.py --slug <slug> --lang <lang> --preview --at-cues
```

Open every QA image (plain and overlay versions) and check:

1. Does any element cross the safe-area box or enter the subtitle zone?
2. Is any text clipped, overlapping other text, axes or titles?
3. Are LaTeX equations overlapping axes or labels?
4. Is the text readable at phone size (not below the `caption` size, except fine print shown through a lens: `docs/STYLE.md`, section 6)?
5. At cue frames: is the animated element actually visible when the voice mentions it?
6. Does the scene match its `visual_plan`?
7. Scenes with a camera move: does each move start at its cue, and is what it shows readable at the end of it? Check a strip of frames across each move as `docs/STYLE.md`, section 6 describes (the QA frames cannot show whether a move is abrupt), and for joins between scenes check that the first frame of the next scene is plain background (and so is the last frame of the first one, except for an edge leaving in a lateral transition).

If anything fails, fix the code and re-render only the affected scenes (`--scenes scene_0X …`; they render in parallel). Maximum 3 iterations per scene; if it still fails, continue and report the issue to the user.

Also run a quick text check: search scene code for string literals that look like visible text (words with spaces outside `S()` / `strings[...]`) and move them to `strings.json`.

## Step 6 — Final render

```bash
manim_engine/.venv/bin/python scripts/render.py --slug <slug> --lang <lang>
```

`render.py` verifies frame counts. Fix any mismatch before stitching.

## Step 7 — Stitch and report

```bash
manim_engine/.venv/bin/python scripts/stitch.py --slug <slug> --lang <lang> --subs <burn|soft|none>
```

Report to the user:

- Final file paths (video(s) and `.srt`).
- Total duration and per-scene engines.
- Assumptions made in Step 1 and any unresolved QA issues.
- What is cheap to change next (subtitles on/off, another language) — see `docs/LOCALIZATION.md`.
