export type Orientation = "vertical" | "horizontal";

export type Cue = { sec: number; frame: number };

export type Word = { text: string; start: number; end: number };

export type SceneTiming = {
  audio?: string;
  duration_sec: number;
  duration_frames: number;
  total_frames: number;
  total_sec: number;
  cues: Record<string, Cue>;
  words?: Word[];
  /** Set only by Root's defaultProps so the Studio preview opens without real timings. */
  placeholder?: boolean;
};

export type SceneProps = {
  slug: string;
  lang: string;
  orientation: Orientation;
  timing: SceneTiming;
  strings: Record<string, string>;
};
