"""Camera path math shared by the Manim camera (camera.py) and mirrored in Remotion (zoomPath.ts).

Pure standard library so the tests run without Manim. A view is ``(x, y, w)``: the point shown at
the center of the content zone and the visible width, in the engine's own units.
"""

from __future__ import annotations

import math

View = tuple[float, float, float]


def ease_in_out_cubic(t: float) -> float:
    """Same curve as Remotion's ``Easing.inOut(Easing.cubic)``."""
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_in_cubic(t: float) -> float:
    """First half of ``ease_in_out_cubic``, stretched: ends at the speed ``ease_out_cubic`` starts with."""
    t = min(max(t, 0.0), 1.0)
    return t ** 3


def ease_out_cubic(t: float) -> float:
    """Second half of ``ease_in_out_cubic``, stretched."""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def view_at(start: View, end: View, t: float) -> View:
    """View at progress ``t`` (0–1, already eased) of a move from ``start`` to ``end``.

    The zoom is geometric around the one point that stays put on screen (the fixed point of the
    move), so zooming in on something never drifts away from it first. Without a change of zoom
    the move is a straight pan.
    """
    x0, y0, w0 = start
    x1, y1, w1 = end
    if abs(math.log(w1 / w0)) < 1e-4:
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w0 + (w1 - w0) * t
    px = (x1 * w0 - x0 * w1) / (w0 - w1)
    py = (y1 * w0 - y0 * w1) / (w0 - w1)
    w = w0 * (w1 / w0) ** t
    f = w / w0
    return px + (x0 - px) * f, py + (y0 - py) * f, w


def through_fade(t: float, fade_from: float) -> float:
    """Opacity of the background closing over a semantic zoom at raw progress ``t`` (0–1)."""
    if t <= fade_from:
        return 0.0
    return ease_in_out_cubic((t - fade_from) / (1 - fade_from))


def lens_tangents(source, at, zoom: float, half_w: float, half_h: float, corner: float):
    """The two outer tangent segments joining a lens to its source, as point pairs.

    The lens is a rectangle centered at ``at`` with half sizes ``half_w`` and ``half_h`` and
    corners rounded with radius ``corner`` (a circle when the three are equal). Its source is the
    same shape scaled by ``1 / zoom`` around ``source``. The two shapes must not overlap.
    """
    if zoom <= 1:
        raise ValueError("lens_tangents: zoom must be greater than 1")
    # Each shape is the rectangle of its corner centers grown by its corner radius.
    ax, ay, r = (half_w - corner) / zoom, (half_h - corner) / zoom, corner / zoom
    gx = max(0.0, abs(at[0] - source[0]) - ax - (half_w - corner))
    gy = max(0.0, abs(at[1] - source[1]) - ay - (half_h - corner))
    if math.hypot(gx, gy) <= r + corner:
        raise ValueError("lens_tangents: the lens overlaps its source")
    # The outer tangents of two homothetic shapes meet at their center of similarity, which lies
    # outside both when they do not overlap: take the extreme tangents from it to the source.
    hx = (zoom * source[0] - at[0]) / (zoom - 1)
    hy = (zoom * source[1] - at[1]) / (zoom - 1)
    ref = math.atan2(source[1] - hy, source[0] - hx)
    best = {}
    for kx, ky in ((source[0] + sx * ax, source[1] + sy * ay) for sx in (-1, 1) for sy in (-1, 1)):
        d = math.hypot(kx - hx, ky - hy)
        base, spread = math.atan2(ky - hy, kx - hx), math.asin(r / d)
        for side in (1, -1):
            a = base + side * spread
            rel = (a - ref + math.pi) % (2 * math.pi) - math.pi
            if side not in best or side * rel > side * best[side][0]:
                best[side] = (rel, a, math.sqrt(d * d - r * r))
    segments = []
    for side in (1, -1):
        _, a, length = best[side]
        px, py = hx + length * math.cos(a), hy + length * math.sin(a)
        segments.append(((px, py), (hx + zoom * (px - hx), hy + zoom * (py - hy))))
    return segments
