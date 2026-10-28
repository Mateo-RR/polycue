import math

from studio.zoom_path import (
    ease_in_cubic, ease_in_out_cubic, ease_out_cubic, lens_tangents, through_fade, view_at,
)


def close(a, b):
    return all(math.isclose(x, y, abs_tol=1e-9) for x, y in zip(a, b))


def screen(point, view):
    """Screen position of a world point, relative to the view center and in view widths."""
    x, y, w = view
    return (point[0] - x) / w, (point[1] - y) / w


def test_view_at_starts_and_ends_on_the_given_views():
    start, end = (0.0, 0.0, 14.0), (3.0, -1.0, 2.0)
    assert close(view_at(start, end, 0), start)
    assert close(view_at(start, end, 1), end)


def test_zoom_keeps_the_fixed_point_still_on_screen():
    start, end = (0.0, 0.0, 14.0), (3.0, -1.0, 2.0)
    px = (end[0] * start[2] - start[0] * end[2]) / (start[2] - end[2])
    py = (end[1] * start[2] - start[1] * end[2]) / (start[2] - end[2])
    for t in (0.1, 0.5, 0.9):
        assert close(screen((px, py), view_at(start, end, t)), screen((px, py), start))


def test_zoom_in_never_moves_the_target_away_from_the_center():
    start, end = (0.0, 0.0, 14.0), (5.0, 2.0, 1.0)
    distances = [math.hypot(*screen(end[:2], view_at(start, end, i / 20))) for i in range(21)]
    assert all(b <= a + 1e-12 for a, b in zip(distances, distances[1:]))
    assert distances[-1] == 0


def test_zoom_scales_geometrically():
    start, end = (0.0, 0.0, 16.0), (0.0, 0.0, 1.0)
    assert math.isclose(view_at(start, end, 0.5)[2], 4.0)


def test_same_zoom_is_a_straight_pan():
    start, end = (0.0, 0.0, 14.0), (2.0, 4.0, 14.0)
    assert close(view_at(start, end, 0.25), (0.5, 1.0, 14.0))


def test_ease_in_out_cubic_matches_remotion():
    assert ease_in_out_cubic(0) == 0 and ease_in_out_cubic(1) == 1
    assert ease_in_out_cubic(0.25) == 4 * 0.25 ** 3
    assert math.isclose(ease_in_out_cubic(0.5), 0.5)
    assert ease_in_out_cubic(-1) == 0 and ease_in_out_cubic(2) == 1


def test_through_fade_starts_late_and_ends_opaque():
    assert through_fade(0.3, 0.5) == 0
    assert through_fade(0.5, 0.5) == 0
    assert math.isclose(through_fade(0.75, 0.5), 0.5)
    assert through_fade(1, 0.5) == 1


def test_pan_out_and_in_join_into_one_ease_in_out_move():
    # pan_out (ease in) then pan_in (ease out), each half the distance and half the time, is one
    # ease_in_out_cubic move: same position and speed at the cut.
    for t in (0.1, 0.3, 0.45):
        assert math.isclose(ease_in_out_cubic(t), ease_in_cubic(2 * t) / 2)
    for t in (0.55, 0.7, 0.9):
        assert math.isclose(ease_in_out_cubic(t), 0.5 + ease_out_cubic(2 * t - 1) / 2)
    h = 1e-6
    assert math.isclose((ease_in_cubic(1) - ease_in_cubic(1 - h)) / h, (ease_out_cubic(h) - ease_out_cubic(0)) / h,
                        rel_tol=1e-4)


def test_semantic_zoom_out_is_the_semantic_zoom_in_played_backwards():
    start, end = (0.0, 0.0, 14.0), (3.0, -1.0, 0.5)
    for t in (0.2, 0.6, 0.9):
        assert close(view_at(end, start, ease_in_out_cubic(t)), view_at(start, end, ease_in_out_cubic(1 - t)))


def corner_circles(center, half_w, half_h, corner, scale=1.0):
    ax, ay = (half_w - corner) * scale, (half_h - corner) * scale
    return [((center[0] + sx * ax, center[1] + sy * ay), corner * scale) for sx in (-1, 1) for sy in (-1, 1)]


def assert_outer_tangents(source, at, zoom, half_w, half_h, corner):
    shapes = corner_circles(source, half_w, half_h, corner, 1 / zoom) + corner_circles(at, half_w, half_h, corner)
    segments = lens_tangents(source, at, zoom, half_w, half_h, corner)
    assert len(segments) == 2
    for p1, p2 in segments:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        n = math.hypot(dx, dy)
        # Signed distance of every corner circle to the line, minus its radius: all on one side,
        # each shape touched.
        gaps = [((k[0] - p1[0]) * dy - (k[1] - p1[1]) * dx) / n for k, _ in shapes]
        side = 1 if sum(gaps) > 0 else -1
        clear = [side * g - r for g, (_, r) in zip(gaps, shapes)]
        assert min(clear) > -1e-9
        assert math.isclose(min(clear[:4]), 0, abs_tol=1e-9) and math.isclose(min(clear[4:]), 0, abs_tol=1e-9)
        # The lens end is the source end scaled like the lens.
        assert math.isclose(p2[0] - at[0], zoom * (p1[0] - source[0]), abs_tol=1e-9)
        assert math.isclose(p2[1] - at[1], zoom * (p1[1] - source[1]), abs_tol=1e-9)


def test_lens_tangents_touch_lens_and_source_from_outside():
    assert_outer_tangents((0.0, 0.0), (5.0, 2.0), 3, 1.5, 1.5, 1.5)  # circle
    assert_outer_tangents((0.0, 0.0), (5.0, 2.0), 3, 2.0, 0.8, 0.0)  # sharp rectangle
    assert_outer_tangents((1.0, -2.0), (-1.5, 3.0), 2.5, 2.4, 0.9, 0.3)  # rounded rectangle
    assert_outer_tangents((0.0, 0.0), (0.0, 4.0), 4, 3.0, 1.0, 0.2)  # straight above, wide


def test_lens_tangents_reject_a_lens_over_its_source():
    for args in (((0, 0), (1.5, 0), 2, 1, 1, 1), ((0, 0), (2.5, 0.5), 3, 2, 0.5, 0.1)):
        try:
            lens_tangents(*args)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {args}")
