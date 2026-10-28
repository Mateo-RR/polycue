// Camera path math. Mirror of manim_engine/studio/zoom_path.py: keep both in sync.

/** [x, y, w]: the point shown at the center of the content zone and the visible width. */
export type View = [number, number, number];

/** Same curve as Easing.inOut(Easing.cubic). */
export const easeInOutCubic = (t: number): number => {
  const c = Math.min(Math.max(t, 0), 1);
  return c < 0.5 ? 4 * c ** 3 : 1 - (-2 * c + 2) ** 3 / 2;
};

/** First half of easeInOutCubic, stretched: ends at the speed easeOutCubic starts with. */
export const easeInCubic = (t: number): number => Math.min(Math.max(t, 0), 1) ** 3;

/** Second half of easeInOutCubic, stretched. */
export const easeOutCubic = (t: number): number => 1 - (1 - Math.min(Math.max(t, 0), 1)) ** 3;

/**
 * View at progress `t` (0–1, already eased) of a move from `start` to `end`. The zoom is geometric
 * around the one point that stays put on screen, so zooming in on something never drifts away
 * from it first. Without a change of zoom the move is a straight pan.
 */
export const viewAt = (start: View, end: View, t: number): View => {
  const [x0, y0, w0] = start;
  const [x1, y1, w1] = end;
  if (Math.abs(Math.log(w1 / w0)) < 1e-4) {
    return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w0 + (w1 - w0) * t];
  }
  const px = (x1 * w0 - x0 * w1) / (w0 - w1);
  const py = (y1 * w0 - y0 * w1) / (w0 - w1);
  const w = w0 * (w1 / w0) ** t;
  const f = w / w0;
  return [px + (x0 - px) * f, py + (y0 - py) * f, w];
};

/** Opacity of the background closing over a semantic zoom at raw progress `t` (0–1). */
export const throughFade = (t: number, fadeFrom: number): number =>
  t <= fadeFrom ? 0 : easeInOutCubic((t - fadeFrom) / (1 - fadeFrom));

type Point = [number, number];

/**
 * The two outer tangent segments joining a lens to its source, as point pairs. The lens is a
 * rectangle centered at `at` with half sizes `halfW`, `halfH` and corners rounded with radius
 * `corner` (a circle when the three are equal); its source is the same shape scaled by `1 / zoom`
 * around `source`. The shapes must not overlap. Same as zoom_path.lens_tangents.
 */
export const lensTangents = (
  source: Point, at: Point, zoom: number, halfW: number, halfH: number, corner: number,
): [Point, Point][] => {
  if (zoom <= 1) throw new Error("lensTangents: zoom must be greater than 1");
  // Each shape is the rectangle of its corner centers grown by its corner radius.
  const [ax, ay, r] = [(halfW - corner) / zoom, (halfH - corner) / zoom, corner / zoom];
  const gx = Math.max(0, Math.abs(at[0] - source[0]) - ax - (halfW - corner));
  const gy = Math.max(0, Math.abs(at[1] - source[1]) - ay - (halfH - corner));
  if (Math.hypot(gx, gy) <= r + corner) throw new Error("lensTangents: the lens overlaps its source");
  // The outer tangents of two homothetic shapes meet at their center of similarity, outside both
  // when they do not overlap: take the extreme tangents from it to the source.
  const hx = (zoom * source[0] - at[0]) / (zoom - 1);
  const hy = (zoom * source[1] - at[1]) / (zoom - 1);
  const ref = Math.atan2(source[1] - hy, source[0] - hx);
  const best = new Map<number, [number, number, number]>();
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      const [kx, ky] = [source[0] + sx * ax, source[1] + sy * ay];
      const d = Math.hypot(kx - hx, ky - hy);
      const [base, spread] = [Math.atan2(ky - hy, kx - hx), Math.asin(r / d)];
      for (const side of [1, -1]) {
        const a = base + side * spread;
        const rel = ((((a - ref + Math.PI) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) - Math.PI;
        const prev = best.get(side);
        if (!prev || side * rel > side * prev[0]) best.set(side, [rel, a, Math.sqrt(d * d - r * r)]);
      }
    }
  }
  return [1, -1].map((side) => {
    const [, a, length] = best.get(side)!;
    const [px, py] = [hx + length * Math.cos(a), hy + length * Math.sin(a)];
    return [[px, py], [hx + zoom * (px - hx), hy + zoom * (py - hy)]] as [Point, Point];
  });
};
