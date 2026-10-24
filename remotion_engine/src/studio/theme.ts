import themeJson from "../../../shared/theme.json";
import type { Orientation } from "./types";

export const theme = themeJson;

export const colors = {
  bg: theme.colors.background,
  primary: theme.colors.primary,
  secondary: theme.colors.secondary,
  accent: theme.colors.accent,
  success: theme.colors.success,
  text: theme.colors.text,
  textMuted: theme.colors.text_muted,
  surface: theme.colors.surface,
  border: theme.colors.border,
} as const;

export const FPS = theme.fps;
export const PADDING_FRAMES = theme.padding_frames;

export const canvas = (orientation: Orientation) => theme.canvas[orientation];

export const typeScale = (orientation: Orientation) => theme.type_scale_px[orientation];

export const fadeInFrames = Math.round(theme.motion.scene_fade_in_sec * FPS);
export const fadeOutFrames = Math.round(theme.motion.scene_fade_out_sec * FPS);

/** Pixel boxes (top/bottom/left/right offsets from the canvas edges) for layout zones. */
export const zoneBoxes = (orientation: Orientation) => {
  const { width, height } = canvas(orientation);
  const margin = (1 - theme.safe_area.ratio) / 2;
  const zones = theme.zones[orientation];
  const sideInset = width * margin;
  const content = {
    left: sideInset,
    right: sideInset,
    top: height * Math.max(zones.content.top, margin),
    bottom: height * Math.max(1 - zones.content.bottom, margin),
  };
  const safe = { left: sideInset, right: sideInset, top: height * margin, bottom: height * margin };
  const subtitles = {
    left: sideInset,
    right: sideInset,
    top: height * zones.subtitles.top,
    bottom: height * (1 - zones.subtitles.bottom),
  };
  return { content, safe, subtitles };
};
