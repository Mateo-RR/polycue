"""CameraScene: a SyncedScene with a moving camera (geometric and semantic zoom, pans, lens)."""

from __future__ import annotations

import math

import numpy as np
from manim import (
    Animation, AnimationGroup, Circle, FadeIn, FadeOut, Group, Line, Mobject, MovingCamera,
    MovingCameraScene, Rectangle, Restore, RoundedRectangle, Transform, VGroup, VMobject, linear,
)
from manim.utils.family import extract_mobject_family_members
from manim.utils.iterables import list_update

from . import theme
from .sync import SyncedScene
from .zoom_path import (
    ease_in_cubic, ease_in_out_cubic, ease_out_cubic, lens_tangents, through_fade, view_at,
)

CAMERA = theme.THEME["camera"]
MASK_Z = 10_000
PIN_Z = 9_000


class _CameraMove(Animation):
    """Moves the camera along zoom_path.view_at; the mask and pinned mobjects follow it."""

    def __init__(self, scene: CameraScene, end, *, start=None, through: bool = False,
                 ease=ease_in_out_cubic, **kwargs):
        self._scene = scene
        self._end = tuple(float(v) for v in end)
        self._start_view = start
        self._through = through
        self._ease = ease
        super().__init__(scene.camera.frame, rate_func=linear, **kwargs)

    def begin(self) -> None:
        if self._start_view is not None:
            self._scene._set_view(self._start_view)
        self._start = self._scene._view()
        super().begin()

    def interpolate_mobject(self, alpha: float) -> None:
        self._scene._set_view(view_at(self._start, self._end, self._ease(alpha)))

    def clean_up_from_scene(self, scene) -> None:
        super().clean_up_from_scene(scene)
        if self._through:
            # The content zone is plain background now (pins faded with the rest): jump back to
            # the default framing.
            scene._pins = []
            scene._set_view(scene._default_view())


class Lens:
    """A magnified, live view of a region of the scene in a circle or a rounded rectangle. Build it
    with ``CameraScene.lens``.

    ``disc`` (the lens outline) drives it: the camera draws the scene magnified inside it whenever
    it is in the scene, so animating the disc animates the lens.
    """

    def __init__(self, scene: CameraScene, source, at, zoom: float, half_w: float, half_h: float,
                 corner: float):
        self.scene = scene
        self.source = np.array([source[0], source[1], 0.0])
        self.zoom = zoom
        self._width = 2 * half_w
        stroke = theme.px(CAMERA["lens_stroke_px"]) / 0.01  # Cairo line width = stroke_width * 0.01
        style = dict(stroke_color=theme.TEXT_MUTED, stroke_width=stroke)

        def shape(k: float) -> VMobject:
            if half_w == half_h == corner:
                return Circle(radius=k * corner, **style)
            if corner == 0:
                return Rectangle(width=2 * k * half_w, height=2 * k * half_h, **style)
            return RoundedRectangle(width=2 * k * half_w, height=2 * k * half_h, corner_radius=k * corner, **style)

        self.ring = shape(1 / zoom).move_to(self.source)
        self.disc = shape(1).set_fill(opacity=0).move_to([at[0], at[1], 0])
        tangents = lens_tangents(self.source[:2], at, zoom, half_w, half_h, corner)
        self.connectors = VGroup(*[Line([*a, 0], [*b, 0], **style) for a, b in tangents])
        self.disc.save_state()
        # Closed: on the source ring and invisible, so the outline fades as it opens and closes.
        self._closed = self.disc.copy().scale(1 / zoom).move_to(self.source).set_stroke(opacity=0)

    def own(self) -> list:
        return [self.ring, self.connectors, self.disc]

    def visible(self) -> bool:
        # Animation groups add their mobjects to the scene inside a Group: look in families.
        return any(m is self.disc for m in self.scene.get_mobject_family_members())

    def draw(self, camera: LensCamera) -> None:
        own = {id(m) for o in self.own() for m in o.get_family()}
        pinned = {id(m) for p in self.scene._pins for m in p[0].get_family()}
        sources = [m for m in camera.get_mobjects_to_display(self.scene.content())
                   if isinstance(m, VMobject) and id(m) not in own and id(m) not in pinned]
        cx, cy, _ = self.disc.get_center()
        m = self.zoom * self.disc.width / self._width  # 1 on the source ring, zoom when open
        ctx = camera.get_cairo_context(camera.pixel_array)
        ctx.save()
        camera.set_cairo_context_path(ctx, self.disc)
        ctx.clip()
        ctx.set_source_rgb(*theme.BG.to_rgb()[::-1])  # the Cairo surface stores BGR, as in Camera
        ctx.paint()
        ctx.translate(cx, cy)
        ctx.scale(m, m)  # strokes grow too, as with the camera zoom
        ctx.translate(-self.source[0], -self.source[1])
        for vm in sources:
            camera.display_vectorized(vm, ctx)
        ctx.restore()
        camera.display_vectorized(self.disc, ctx)


class LensCamera(MovingCamera):
    """MovingCamera that also draws the open lenses of its scene, over everything else."""

    def __init__(self, **kwargs):
        self.lenses: list[Lens] = []
        super().__init__(**kwargs)

    def capture_mobjects(self, mobjects, **kwargs) -> None:
        mobjects = list(mobjects)
        super().capture_mobjects(mobjects, **kwargs)
        # Only in the pass that draws the disc: during animations Manim draws still mobjects once
        # into a cached background, and an open lens always counts as moving (CameraScene), so it
        # is redrawn every frame on top instead of being frozen into that background.
        captured = {id(m) for m in extract_mobject_family_members(mobjects)}
        for lens in self.lenses:
            if id(lens.disc) in captured and lens.visible():
                lens.draw(self)


class CameraScene(SyncedScene, MovingCameraScene):
    """SyncedScene whose camera can zoom and pan. Everything is clipped to the content zone.

    A view is ``(x, y, w)``: the point shown at the center of the content zone and the visible
    frame width. Move the camera only through the methods below, so the mask and pinned mobjects
    follow it.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("camera_class", LensCamera)
        super().__init__(**kwargs)

    def setup(self):
        super().setup()
        frame = self.camera.frame
        self._fw = frame.width
        self._cc = theme.content_center()
        # Pins: (mobject, offset from the frame center, width) as they look at the default framing.
        self._pins: list[tuple] = []
        self._mask = self._build_mask(frame.width, frame.height)
        self._mask_pin = (self._mask, self._mask.get_center(), self._mask.width)
        self.add(self._mask)

    # ---- view -----------------------------------------------------------

    def _default_view(self):
        return float(self._cc[0]), float(self._cc[1]), self._fw

    def _view(self):
        frame = self.camera.frame
        k = frame.width / self._fw
        x, y, _ = frame.get_center() + k * self._cc
        return float(x), float(y), float(frame.width)

    def _set_view(self, view) -> None:
        x, y, w = view
        k = w / self._fw
        frame = self.camera.frame
        frame.scale_to_fit_width(w)
        frame.move_to(np.array([x, y, 0.0]) - k * self._cc)
        self._follow()

    def _follow(self) -> None:
        # Absolute, not incremental: another animation may have reset a pinned mobject this frame.
        frame = self.camera.frame
        k = frame.width / self._fw
        center = frame.get_center()
        for mob, offset, width in [self._mask_pin, *self._pins]:
            if width > 0 and mob.width > 0:
                mob.scale(k * width / mob.width)
            mob.move_to(center + k * offset)

    def update_mobjects(self, dt: float) -> None:
        # Runs after every animation of the frame has been interpolated, so pins win.
        super().update_mobjects(dt)
        self._follow()

    def _build_mask(self, fw: float, fh: float) -> VGroup:
        left, right, top, bottom = theme.content_box()
        x0, x1, y0, y1 = -fw / 2 - 1, fw / 2 + 1, -fh / 2 - 1, fh / 2 + 1

        def band(a, b, c, d):
            return Rectangle(width=b - a, height=d - c, fill_color=theme.BG, fill_opacity=1,
                             stroke_width=0).move_to([(a + b) / 2, (c + d) / 2, 0])

        mask = VGroup(band(x0, x1, top, y1), band(x0, x1, y0, bottom),
                      band(x0, left, y0, y1), band(right, x1, y0, y1))
        mask.set_z_index(MASK_Z)
        return mask

    def _ensure_mask(self) -> None:
        if self._mask not in self.mobjects:
            self._mask.set_fill(opacity=1)
            self.add(self._mask)

    def _content_size(self):
        left, right, top, bottom = theme.content_box()
        return right - left, top - bottom

    def _target_view(self, target, fill, zoom):
        is_mob = isinstance(target, Mobject)
        if zoom is None:
            if not is_mob:
                raise ValueError("a point target needs zoom=")
            fill = CAMERA["fill"] if fill is None else fill
            cw, ch = self._content_size()
            k = max(target.width / (cw * fill), target.height / (ch * fill))
        else:
            k = 1 / zoom
        x, y = (target.get_center() if is_mob else np.asarray(target, dtype=float))[:2]
        return float(x), float(y), k * self._fw

    def _cover_view(self, target: Mobject):
        # Zoomed in until the convex target covers the content zone.
        cw, ch = self._content_size()
        k = min(target.width, target.height) / math.hypot(cw, ch)
        x, y = target.get_center()[:2]
        return float(x), float(y), k * self._fw

    # ---- mobject bookkeeping ------------------------------------------

    def content(self) -> list:
        """Scene mobjects without the camera frame and the mask. Use it instead of self.mobjects."""
        return [m for m in self.mobjects if m is not self._mask and m is not self.camera.frame]

    def _fade_targets(self) -> list:
        return self.content()

    def get_moving_mobjects(self, *animations):
        moving = super().get_moving_mobjects(*animations)
        # Redraw the mask and open lenses over anything that moves, or they would be drawn below it.
        if moving:
            on_top = [self._mask] if self._mask in self.mobjects else []
            on_top += [lens.disc for lens in self.camera.lenses if lens.visible()]
            moving = list_update(moving, on_top)
        return moving

    def pin(self, *mobjects: Mobject) -> None:
        """Keep mobjects fixed on screen while the camera moves (level labels, scale bars).

        Place them first, where they should stay; they are drawn above the content.
        """
        frame = self.camera.frame
        k = frame.width / self._fw
        for mob in mobjects:
            if mob.z_index == 0:
                mob.set_z_index(PIN_Z)
            self._pins.append((mob, (mob.get_center() - frame.get_center()) / k, mob.width / k))

    # ---- geometric zoom -------------------------------------------------

    def zoom_to(self, target, *, fill: float | None = None, zoom: float | None = None) -> Animation:
        """Geometric zoom: frame ``target`` in the content zone.

        ``target`` is a mobject or a point. With a mobject and no ``zoom``, it ends up filling
        ``fill`` (default ``theme.json → camera.fill``) of the content zone. ``zoom`` is relative
        to the default framing (2 = twice as big). Use as ``self.play(self.zoom_to(...), run_time=…)``.
        Two ``zoom_to`` with the same ``zoom`` make a straight pan.
        """
        self._ensure_mask()
        return _CameraMove(self, self._target_view(target, fill, zoom))

    def zoom_reset(self) -> Animation:
        """Back to the default framing."""
        self._ensure_mask()
        return _CameraMove(self, self._default_view())

    def start_at(self, target, *, fill: float | None = None, zoom: float | None = None) -> None:
        """Put the camera on ``target`` without a move (same arguments as ``zoom_to``).

        Call it before anything is shown, to open a scene on a detail and then pull back with
        ``zoom_reset`` (a reveal).
        """
        self._ensure_mask()
        self._set_view(self._target_view(target, fill, zoom))

    # ---- semantic zoom --------------------------------------------------

    def zoom_through(self, target: Mobject) -> Animation:
        """Semantic zoom in, first half: dive into ``target`` until the background closes in.

        The camera zooms in until ``target`` covers the content zone (works for convex shapes:
        circles, squares, cards), and everything fades to the background color during the last
        part (``camera.through_fade_from``). After it the scene is empty and the camera is back at
        the default framing: bring in the next level with ``emerge``.
        """
        self._ensure_mask()
        fade_from = CAMERA["through_fade_from"]
        fades = [FadeOut(m, rate_func=lambda a: through_fade(a, fade_from)) for m in self.content()]
        return AnimationGroup(_CameraMove(self, self._cover_view(target), through=True), *fades)

    def emerge(self, *mobjects: Mobject) -> Animation:
        """Semantic zoom in, second half: the new level grows from the center of the content zone."""
        s = CAMERA["emerge_scale"]
        x, y, _ = self._view()
        center = np.array([x, y, 0.0])
        own = Group(*mobjects).get_center()
        return FadeIn(*mobjects, shift=(1 - s) * (own - center), scale=s, rate_func=ease_in_out_cubic)

    def recede(self) -> Animation:
        """Semantic zoom out, first half: the current level shrinks into the center and fades out.

        Pinned mobjects only fade. After it the scene is empty: bring in the level above with
        ``zoom_out_of``.
        """
        s = CAMERA["emerge_scale"]
        x, y, _ = self._view()
        center = np.array([x, y, 0.0])
        pinned = [p[0] for p in self._pins]
        self._pins = []  # the camera does not move while receding
        anims = []
        for m in self.content():
            if m in pinned:
                anims.append(FadeOut(m, rate_func=ease_in_out_cubic))
            else:
                anims.append(FadeOut(m, shift=(1 - s) * (center - m.get_center()), scale=s,
                                     rate_func=ease_in_out_cubic))
        return AnimationGroup(*anims)

    def zoom_out_of(self, target: Mobject, *mobjects: Mobject) -> Animation:
        """Semantic zoom out, second half: ``zoom_through`` played backwards.

        ``mobjects`` are the level above (not in the scene yet), and ``target`` is the element of
        it that the previous level was inside (a convex shape). The camera starts inside ``target``
        on a plain background and pulls back to the default framing while the level above appears.
        Pin its labels with ``pin`` before calling this.
        """
        self._ensure_mask()
        fade_from = CAMERA["through_fade_from"]
        fades = [FadeIn(m, rate_func=lambda a: 1 - through_fade(1 - a, fade_from)) for m in mobjects]
        return AnimationGroup(_CameraMove(self, self._default_view(), start=self._cover_view(target)), *fades)

    # ---- transitions between scenes -------------------------------------

    def _pan_shift(self, direction) -> np.ndarray:
        d = np.asarray(direction, dtype=float)[:2]
        if np.count_nonzero(d) != 1:
            raise ValueError("pan direction must be LEFT, RIGHT, UP or DOWN")
        k = self._view()[2] / self._fw
        cw, ch = self._content_size()
        return np.sign(d) * np.array([cw, ch]) * k

    def pan_in(self, direction, *mobjects: Mobject) -> None:
        """Start the scene with the camera arriving while moving towards ``direction``.

        Use it instead of ``fade_in`` at the very start, when the previous scene ended with
        ``pan_out`` in the same direction: together they read as one sideways move, cut on a plain
        background. Lasts ``camera.pan_sec``.
        """
        self._ensure_mask()
        x, y, w = self._default_view()
        dx, dy = self._pan_shift(direction)
        self.add(*mobjects)
        self.play(_CameraMove(self, (x, y, w), start=(x - dx, y - dy, w), ease=ease_out_cubic),
                  run_time=self.frames(CAMERA["pan_sec"]))

    def pan_out(self, direction) -> None:
        """End the scene with the camera leaving towards ``direction``, until only background shows.

        Use it instead of ``finish()``. The next scene starts with ``pan_in`` (or ``panIn`` in
        Remotion) in the same direction. Pinned mobjects leave with the content.
        """
        self._ensure_mask()
        n = round(CAMERA["pan_sec"] * self.fps)
        total = round(self.total_sec * self.fps)
        self.wait_until((total - n) / self.fps)
        self._pins = []
        x, y, w = self._view()
        dx, dy = self._pan_shift(direction)
        self.play(_CameraMove(self, (x + dx, y + dy, w), ease=ease_in_cubic), run_time=self._animated_run_time(n))
        self.finish()

    # ---- lens -------------------------------------------------------------

    def lens(self, source, at, *, zoom: float | None = None, radius: float | None = None,
             size=None) -> Lens:
        """A lens showing the region around ``source`` magnified, centered at ``at``.

        ``source`` and ``at`` are points or mobjects (their centers). The lens is a circle of
        ``radius`` (default ``camera.lens_radius`` of the content zone's smaller side) or, with
        ``size=(width, height)``, a rectangle with rounded corners (``camera.lens_corner_px``),
        for long details such as a line of text or a stretch of an axis. ``zoom`` is its
        magnification (default ``camera.lens_zoom``). The lens must fit in the content zone and
        must not overlap the region it magnifies. Show it with ``open_lens`` and hide it with
        ``close_lens``; use it at the default framing.
        """
        def point(p):
            return (p.get_center() if isinstance(p, Mobject) else np.asarray(p, dtype=float))[:2]

        cw, ch = self._content_size()
        zoom = CAMERA["lens_zoom"] if zoom is None else zoom
        if size is None:
            half_w = half_h = corner = CAMERA["lens_radius"] * min(cw, ch) if radius is None else radius
        else:
            half_w, half_h = size[0] / 2, size[1] / 2
            corner = min(theme.px(CAMERA["lens_corner_px"]), half_w, half_h)
        src, at = point(source), point(at)
        left, right, top, bottom = theme.content_box()
        if not (left <= at[0] - half_w and at[0] + half_w <= right and bottom <= at[1] - half_h and at[1] + half_h <= top):
            raise ValueError("lens: the lens does not fit in the content zone")
        lens = Lens(self, src, at, zoom, half_w, half_h, corner)
        self.camera.lenses.append(lens)
        return lens

    def open_lens(self, lens: Lens) -> Animation:
        """The lens lifts out of its source ring and moves to its place, growing."""
        lens.disc.become(lens._closed)
        return AnimationGroup(
            Restore(lens.disc, rate_func=ease_in_out_cubic),
            FadeIn(lens.ring, rate_func=ease_in_out_cubic),
            FadeIn(lens.connectors, rate_func=lambda a: through_fade(a, 0.5)),
        )

    def close_lens(self, lens: Lens) -> Animation:
        """``open_lens`` backwards: the lens shrinks back onto its source and disappears."""
        return AnimationGroup(
            Transform(lens.disc, lens._closed.copy(), rate_func=ease_in_out_cubic, remover=True),
            FadeOut(lens.ring, rate_func=ease_in_out_cubic),
            FadeOut(lens.connectors, rate_func=lambda a: ease_in_out_cubic(min(1.0, 2 * a))),
        )
