import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FONT_SANS } from "./fonts";
import { colors, fadeInFrames, fadeOutFrames } from "./theme";
import type { SceneTiming } from "./types";

/** Scene wrapper: theme background, fade-in at start, fade-out ending on the last frame. */
export const Fade: React.FC<{ timing: SceneTiming; children?: React.ReactNode }> = ({ timing, children }) => {
  const frame = useCurrentFrame();
  const last = timing.total_frames - 1;
  const opacity = Math.min(
    interpolate(frame, [0, fadeInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
    interpolate(frame, [last - fadeOutFrames, last], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  );
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, fontFamily: FONT_SANS, color: colors.text }}>
      <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
