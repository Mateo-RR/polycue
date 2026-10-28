import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { canvas, colors, FPS, theme, zoneBoxes } from "./theme";
import type { Orientation, SceneTiming } from "./types";
import { easeInCubic, easeInOutCubic, easeOutCubic, lensTangents, throughFade, View, viewAt } from "./zoomPath";

/** A framing: the point of the content zone (fractions, 0–1) at its center, and the zoom (1 = default). */
export type Framing = { x?: number; y?: number; zoom?: number };

/**
 * One camera move, starting at frame `at` (usually a `useCue`) and lasting `frames`.
 * `x`/`y`/`zoom`: the framing it ends on; omitted values keep the previous ones. Build the special
 * moves with the helpers below (`zoomThrough`, `zoomOutOf`, `panIn`, `panOut`) rather than by hand.
 */
export type CameraMove = Framing & {
  at: number;
  frames: number;
  /** Jump to this framing when the move starts. */
  from?: Framing;
  /** Instead of x/y: move by this many visible content-zone widths/heights. */
  shift?: [number, number];
  ease?: "inOut" | "in" | "out";
  /** Semantic zoom in: the background closes in, then the camera renders nothing. */
  through?: boolean;
  /** Semantic zoom out: the background opens; the camera renders nothing before this move. */
  outOf?: boolean;
  /** Transition between scenes: pinned elements travel with the content. */
  pan?: boolean;
};

export type PanDirection = "left" | "right" | "up" | "down";

const centered: React.CSSProperties = { alignItems: "center", justifyContent: "center" };
const EASE = { inOut: easeInOutCubic, in: easeInCubic, out: easeOutCubic };
const DIRECTIONS: Record<PanDirection, [number, number]> = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] };

/** Width and height in px of the content zone, the area a `<Camera>` fills and clips. */
export const contentSize = (orientation: Orientation) => {
  const { width, height } = canvas(orientation);
  const { content } = zoneBoxes(orientation);
  return { w: width - content.left - content.right, h: height - content.top - content.bottom };
};

/** Frames of each half of a lateral transition between scenes (`camera.pan_sec`). */
export const panFrames = Math.round(theme.camera.pan_sec * FPS);

/** Back to the default framing. */
export const zoomReset = (at: number, frames: number): CameraMove => ({ at, frames, x: 0.5, y: 0.5, zoom: 1 });

// Zoom at which a convex element whose smaller side is `size` px covers the content zone.
const coverZoom = (size: number, orientation: Orientation) => {
  const { w, h } = contentSize(orientation);
  return Math.hypot(w, h) / size;
};

/**
 * Semantic zoom in, first half: dive into a convex element (circle, square, card) whose smaller
 * side is `size` px, centered at `x`/`y`, until it covers the content zone while the background
 * closes in. Afterwards the `<Camera>` shows nothing: bring in the next level with `<Emerge>`.
 */
export const zoomThrough = (
  move: { at: number; frames: number; x: number; y: number; size: number },
  orientation: Orientation,
): CameraMove => ({ at: move.at, frames: move.frames, x: move.x, y: move.y, zoom: coverZoom(move.size, orientation), through: true });

/**
 * Semantic zoom out, second half: `zoomThrough` played backwards. The `<Camera>` holds the level
 * above and renders nothing before this move; it starts inside the element (`size`, `x`, `y` as in
 * `zoomThrough`) on a plain background and pulls back to the default framing.
 */
export const zoomOutOf = (
  move: { at: number; frames: number; x: number; y: number; size: number },
  orientation: Orientation,
): CameraMove => ({
  at: move.at,
  frames: move.frames,
  from: { x: move.x, y: move.y, zoom: coverZoom(move.size, orientation) },
  x: 0.5,
  y: 0.5,
  zoom: 1,
  outOf: true,
});

/**
 * Start of a scene: the camera arrives moving towards `direction`. Pairs with `panOut` (or Manim's
 * `pan_out`) in the same direction at the end of the previous scene. Use `<Fade fadeIn={false}>`.
 */
export const panIn = (direction: PanDirection): CameraMove => {
  const [dx, dy] = DIRECTIONS[direction];
  return { at: 0, frames: panFrames, from: { x: 0.5 - dx, y: 0.5 - dy, zoom: 1 }, x: 0.5, y: 0.5, zoom: 1, ease: "out", pan: true };
};

/**
 * End of a scene: the camera leaves towards `direction` until only background shows. The next scene
 * starts with `panIn` (or Manim's `pan_in`). Use `<Fade fadeOut={false}>`. Like Manim, the last
 * frame is one step before the end of the move: the next scene's first frame (background only) is
 * that end, so the motion stays continuous across the cut.
 */
export const panOut = (direction: PanDirection, timing: SceneTiming): CameraMove => ({
  at: timing.total_frames - panFrames,
  frames: panFrames,
  shift: DIRECTIONS[direction],
  ease: "in",
  pan: true,
});

const framingView = (f: Framing, base: View, w: number, h: number): View => [
  f.x === undefined ? base[0] : f.x * w,
  f.y === undefined ? base[1] : f.y * h,
  f.zoom === undefined ? base[2] : w / f.zoom,
];

/**
 * Camera state at `frame`: the view (content-zone px), how much background covers it, whether it
 * renders nothing, and how far pinned elements travel (px) during a transition between scenes.
 */
export const cameraAt = (moves: CameraMove[], frame: number, w: number, h: number, initial?: Framing) => {
  const home: View = [w / 2, h / 2, w];
  let view: View = initial ? framingView(initial, home, w, h) : home;
  const sorted = [...moves].sort((a, b) => a.at - b.at);
  const idle = { view, cover: 0, hidden: false, pinShift: [0, 0] as [number, number] };
  if (sorted.length && sorted[0].outOf && frame < sorted[0].at) return { ...idle, hidden: true };
  let pinShift: [number, number] = [0, 0];
  for (const m of sorted) {
    if (frame < m.at) break;
    const start = m.from ? framingView(m.from, view, w, h) : view;
    const end: View = m.shift
      ? [start[0] + m.shift[0] * start[2], start[1] + (m.shift[1] * start[2] * h) / w, start[2]]
      : framingView(m, start, w, h);
    const raw = Math.min(1, (frame - m.at) / Math.max(1, m.frames));
    const now = viewAt(start, end, EASE[m.ease ?? "inOut"](raw));
    const z = w / now[2];
    // Pinned elements stay attached to the framing the content is arriving at or leaving.
    const anchor = m.from ? end : start;
    pinShift = m.pan ? [(anchor[0] - now[0]) * z, (anchor[1] - now[1]) * z] : [0, 0];
    if (raw < 1) {
      const f = theme.camera.through_fade_from;
      const cover = m.through ? throughFade(raw, f) : m.outOf ? throughFade(1 - raw, f) : 0;
      return { view: now, cover, hidden: false, pinShift };
    }
    if (m.through) return { ...idle, view: home, hidden: true };
    view = end;
  }
  return { view, cover: 0, hidden: false, pinShift };
};

/**
 * Camera. Goes inside `<SafeArea>`: fills the content zone, clips to it and lays children out the
 * same way. `initial`: framing before the first move (open on a detail, then `zoomReset` to
 * reveal the rest). `pinned` stays fixed on screen (level labels, scale bars) but, like the content,
 * fades out during a semantic zoom; anything outside the `<Camera>` is not affected by it.
 */
export const Camera: React.FC<{
  orientation: Orientation;
  moves: CameraMove[];
  initial?: Framing;
  pinned?: React.ReactNode;
  children?: React.ReactNode;
}> = ({ orientation, moves, initial, pinned, children }) => {
  const frame = useCurrentFrame();
  const { w, h } = contentSize(orientation);
  const { view, cover, hidden, pinShift } = cameraAt(moves, frame, w, h, initial);
  if (hidden) return null;
  const z = w / view[2];
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill
        style={{ ...centered, transformOrigin: "0 0", transform: `translate(${w / 2 - view[0] * z}px, ${h / 2 - view[1] * z}px) scale(${z})` }}
      >
        {children}
      </AbsoluteFill>
      {pinned ? <AbsoluteFill style={{ transform: `translate(${pinShift[0]}px, ${pinShift[1]}px)` }}>{pinned}</AbsoluteFill> : null}
      {cover > 0 ? <AbsoluteFill style={{ backgroundColor: colors.bg, opacity: cover }} /> : null}
    </AbsoluteFill>
  );
};

/** Semantic zoom in, second half: the next level grows from the center of the content zone. */
export const Emerge: React.FC<{ at: number; frames: number; children?: React.ReactNode }> = ({ at, frames, children }) => {
  const frame = useCurrentFrame();
  if (frame < at) return null;
  const t = easeInOutCubic((frame - at) / Math.max(1, frames));
  const s = theme.camera.emerge_scale;
  return <AbsoluteFill style={{ ...centered, opacity: t, transform: `scale(${s + (1 - s) * t})` }}>{children}</AbsoluteFill>;
};

/**
 * Semantic zoom out, first half: the current level shrinks into the center of the content zone and
 * fades out; `pinned` (its level label) only fades. Afterwards nothing is rendered: bring in the
 * level above with a `<Camera>` whose first move is `zoomOutOf`.
 */
export const Recede: React.FC<{ at: number; frames: number; pinned?: React.ReactNode; children?: React.ReactNode }> = ({
  at,
  frames,
  pinned,
  children,
}) => {
  const frame = useCurrentFrame();
  if (frame >= at + frames) return null;
  const t = frame < at ? 0 : easeInOutCubic((frame - at) / Math.max(1, frames));
  const s = theme.camera.emerge_scale;
  return (
    <AbsoluteFill style={{ opacity: 1 - t }}>
      <AbsoluteFill style={{ ...centered, transform: `scale(${1 - (1 - s) * t})` }}>{children}</AbsoluteFill>
      {pinned ? <AbsoluteFill>{pinned}</AbsoluteFill> : null}
    </AbsoluteFill>
  );
};

type Point = { x: number; y: number };

/**
 * Lens: the region around `source` magnified, centered at `center` (both fractions of the content
 * zone), on top of everything. Goes inside `<SafeArea>`, after the `<Camera>`, with the same
 * children (it renders them a second time, live). Opens at `at` over `frames` (it lifts out of its
 * source ring) and closes at `until` the same way backwards. A circle of `radius` px (default
 * `camera.lens_radius` of the content zone's smaller side) or, with `size` ({ w, h } in px), a
 * rectangle with rounded corners (`camera.lens_corner_px`) for long details. `zoom` default
 * `camera.lens_zoom`. Use it at the default framing; it must fit in the content zone and not
 * overlap its source.
 */
export const Lens: React.FC<{
  orientation: Orientation;
  at: number;
  frames: number;
  until?: number;
  source: Point;
  center: Point;
  zoom?: number;
  radius?: number;
  size?: { w: number; h: number };
  children?: React.ReactNode;
}> = ({ orientation, at, frames, until, source, center, zoom, radius, size, children }) => {
  const frame = useCurrentFrame();
  const { w, h } = contentSize(orientation);
  const Z = zoom ?? theme.camera.lens_zoom;
  const R = radius ?? theme.camera.lens_radius * Math.min(w, h);
  // Half sizes and corner radius of the open lens; a circle is a square with round corners.
  const [hw, hh] = size ? [size.w / 2, size.h / 2] : [R, R];
  const corner = size ? Math.min(theme.camera.lens_corner_px, hw, hh) : R;
  const s: [number, number] = [source.x * w, source.y * h];
  const c: [number, number] = [center.x * w, center.y * h];
  const tangents = lensTangents(s, c, Z, hw, hh, corner);
  const closing = until !== undefined && frame >= until;
  if (frame < at || (closing && frame >= until + frames)) return null;
  const raw = Math.min(1, (frame - (closing ? until : at)) / Math.max(1, frames));
  const t = closing ? 1 - easeInOutCubic(raw) : easeInOutCubic(raw);
  const ringOpacity = t;
  const linkOpacity = closing ? 1 - easeInOutCubic(Math.min(1, 2 * raw)) : throughFade(raw, 0.5);
  // The lens body moves from the source ring (magnification 1) to its place (magnification Z).
  const cx = s[0] + (c[0] - s[0]) * t;
  const cy = s[1] + (c[1] - s[1]) * t;
  const q = 1 / Z + (1 - 1 / Z) * t; // size relative to the open lens
  const m = Z * q;
  const stroke = theme.camera.lens_stroke_px;
  const line = { stroke: colors.textMuted, strokeWidth: stroke, fill: "none" };
  return (
    <AbsoluteFill>
      <svg width={w} height={h} style={{ position: "absolute", left: 0, top: 0 }}>
        <rect x={s[0] - hw / Z} y={s[1] - hh / Z} width={(2 * hw) / Z} height={(2 * hh) / Z} rx={corner / Z} opacity={ringOpacity} {...line} />
        {tangents.map(([a, b], i) => (
          <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} opacity={linkOpacity} {...line} />
        ))}
      </svg>
      <AbsoluteFill style={{ clipPath: `inset(${cy - hh * q}px ${w - cx - hw * q}px ${h - cy - hh * q}px ${cx - hw * q}px round ${corner * q}px)` }}>
        <AbsoluteFill style={{ backgroundColor: colors.bg }} />
        <AbsoluteFill style={{ ...centered, transformOrigin: "0 0", transform: `translate(${cx - s[0] * m}px, ${cy - s[1] * m}px) scale(${m})` }}>
          {children}
        </AbsoluteFill>
      </AbsoluteFill>
      <svg width={w} height={h} style={{ position: "absolute", left: 0, top: 0 }}>
        <rect x={cx - hw * q} y={cy - hh * q} width={2 * hw * q} height={2 * hh * q} rx={corner * q} opacity={ringOpacity} {...line} />
      </svg>
    </AbsoluteFill>
  );
};
