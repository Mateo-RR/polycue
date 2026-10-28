import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FONT_SANS } from "./fonts";
import { colors, fadeInFrames, fadeOutFrames } from "./theme";
import type { SceneTiming } from "./types";

/**
 * Scene wrapper: theme background, fade-in at start, fade-out ending on the last frame. Turn either
 * fade off where the scene joins the next one with the camera (`<Emerge>` or `panIn` at the start;
 * `zoomThrough` or `panOut` at the end): the camera move already starts or ends on plain background.
 */
export const Fade: React.FC<{ timing: SceneTiming; fadeIn?: boolean; fadeOut?: boolean; children?: React.ReactNode }> = ({
  timing,
  fadeIn = true,
  fadeOut = true,
  children,
}) => {
  const frame = useCurrentFrame();
  const last = timing.total_frames - 1;
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
  const opacity = Math.min(
    fadeIn ? interpolate(frame, [0, fadeInFrames], [0, 1], clamp) : 1,
    fadeOut ? interpolate(frame, [last - fadeOutFrames, last], [1, 0], clamp) : 1,
  );
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, fontFamily: FONT_SANS, color: colors.text }}>
      <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
