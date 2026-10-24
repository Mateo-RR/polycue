"""SyncedScene: base class that ties a Manim scene to its voiceover timings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from manim import FadeIn, FadeOut, Scene, logger

from . import theme

REPO_ROOT = Path(__file__).resolve().parents[2]

# Configure at import time: scripts/render.py sets the env vars before Manim
# imports the scene module, and the camera is built from config before setup().
theme.configure()


def timings_path() -> Path:
    override = os.environ.get("STUDIO_TIMINGS")
    if override:
        return Path(override)
    slug = os.environ.get("STUDIO_SLUG")
    lang = os.environ.get("STUDIO_LANG")
    if not slug or not lang:
        raise RuntimeError("STUDIO_SLUG and STUDIO_LANG must be set. Render scenes through scripts/render.py.")
    return REPO_ROOT / "projects" / slug / "locales" / lang / "timings.json"


class SyncedScene(Scene):
    """Scene whose length and cue times come from timings.json.

    Every ``construct()`` must end with ``self.finish()``.
    """

    scene_id = "scene_XX"

    def setup(self):
        theme.configure()
        path = timings_path()
        if not path.exists():
            raise FileNotFoundError(f"timings not found: {path}. Run scripts/tts_sync.py first.")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if self.scene_id not in data["scenes"]:
            raise KeyError(f"{self.scene_id} not in {path}; available: {list(data['scenes'])}")
        t = data["scenes"][self.scene_id]
        self.timing = t
        self.duration_sec = float(t["duration_sec"])
        self.total_sec = t["total_frames"] / data["fps"]
        self.cues = {name: float(c["sec"]) for name, c in t.get("cues", {}).items()}
        self.fps = theme.config.frame_rate
        self.fade_in_sec = theme.THEME["motion"]["scene_fade_in_sec"]
        self.fade_out_sec = theme.THEME["motion"]["scene_fade_out_sec"]

    # ---- time helpers -------------------------------------------------

    def now(self) -> float:
        return self.renderer.time

    def _frames_now(self) -> int:
        return round(self.now() * self.fps)

    def _resolve(self, name_or_seconds) -> float:
        if isinstance(name_or_seconds, (int, float)):
            return float(name_or_seconds)
        if name_or_seconds not in self.cues:
            raise KeyError(
                f"Unknown cue {name_or_seconds!r} in {self.scene_id}; available cues: {list(self.cues)}"
            )
        return self.cues[name_or_seconds]

    def cue(self, name: str) -> float:
        return self._resolve(name)

    def _animated_run_time(self, n_frames: int) -> float:
        # Manim writes ceil(run_time * fps) frames for animations; aim half a
        # frame short so float error never adds a frame.
        return 1 / self.fps if n_frames <= 1 else (n_frames - 0.5) / self.fps

    def _is_static(self) -> bool:
        return not (
            self.always_update_mobjects
            or self.updaters
            or any(m.has_time_based_updater() for m in self.get_mobject_family_members())
        )

    def _wait_frames(self, n_frames: int) -> None:
        if n_frames <= 0:
            return
        if self._is_static():
            # Frozen waits write int(duration * fps) frames: aim half a frame long.
            self.wait((n_frames + 0.5) / self.fps, frozen_frame=True)
        else:
            self.wait(self._animated_run_time(n_frames), frozen_frame=False)

    def wait_until(self, name_or_seconds) -> None:  # overrides Scene.wait_until on purpose
        target = self._resolve(name_or_seconds)
        n = round(target * self.fps) - self._frames_now()
        if n < -1:
            logger.warning(
                f"{self.scene_id}: already {-n / self.fps:.2f}s past {name_or_seconds!r}; not waiting"
            )
            return
        self._wait_frames(n)

    def until(self, name_or_seconds, min: float = 0.2, gap: float = 0.0, cap: float | None = None) -> float:
        """Seconds until a cue/time, quantized to whole frames, usable as ``run_time``.

        ``gap`` ends the animation that many seconds before the target (STYLE asks for
        0.3 s between cue-driven animations); ``cap`` limits the duration.
        """
        target = self._resolve(name_or_seconds) - gap
        n = round(target * self.fps) - self._frames_now()
        if cap is not None and n > round(cap * self.fps):
            n = round(cap * self.fps)
        n = max(n, round(min * self.fps), 1)
        return self._animated_run_time(n)

    def frames(self, seconds: float) -> float:
        """A fixed duration (transitions, fade-in) quantized to whole frames, for ``run_time``."""
        return self._animated_run_time(max(1, round(seconds * self.fps)))

    def fade_in(self, *mobjects, **kwargs) -> None:
        """Fade mobjects in over motion.scene_fade_in_sec."""
        self.play(*[FadeIn(m, **kwargs) for m in mobjects], run_time=self.frames(self.fade_in_sec))

    def finish(self) -> None:
        """Fade everything out during the padding and end exactly at total_sec."""
        total_frames = round(self.total_sec * self.fps)
        over = self._frames_now() - total_frames
        if over > 1:
            raise RuntimeError(
                f"{self.scene_id} already lasts {self.now():.3f}s, beyond total_sec={self.total_sec:.3f}s"
            )
        fade_frames = round(self.fade_out_sec * self.fps)
        start_fade = total_frames - fade_frames
        if self._frames_now() < start_fade:
            self._wait_frames(start_fade - self._frames_now())
        remaining = total_frames - self._frames_now()
        # Freeze always_redraw/updaters so they don't override the fade-out.
        for m in self.mobjects:
            m.clear_updaters()
        if self.mobjects and remaining > 0:
            n = min(fade_frames, remaining)
            self.play(*[FadeOut(m) for m in self.mobjects], run_time=self._animated_run_time(n))
        self.clear()
        self._wait_frames(total_frames - self._frames_now())
        drift = self._frames_now() - total_frames
        if drift != 0:
            logger.warning(f"{self.scene_id}: ended {drift:+d} frames off total_frames={total_frames}")
