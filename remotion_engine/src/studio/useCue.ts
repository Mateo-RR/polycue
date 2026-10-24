import { Easing, interpolate, useCurrentFrame } from "remotion";
import type { SceneTiming } from "./types";

/** Frame (at 60 fps) where a narration cue starts. */
export const useCue = (name: string, timing: SceneTiming): number => {
  const cue = timing.cues[name];
  if (cue) return cue.frame;
  if (timing.placeholder) {
    // Studio preview without real timings: spread unknown cues over the first second.
    return 30;
  }
  throw new Error(`Unknown cue "${name}"; available cues: ${Object.keys(timing.cues).join(", ") || "(none)"}`);
};

/** 0 → 1 eased progress over `durationFrames`, starting at the cue. */
export const useCueProgress = (name: string, durationFrames: number, timing: SceneTiming): number => {
  const frame = useCurrentFrame();
  const start = useCue(name, timing);
  return interpolate(frame, [start, start + Math.max(1, durationFrames)], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};
