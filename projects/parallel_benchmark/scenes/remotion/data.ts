// Average seconds per pipeline step for projects/monte_carlo_pi, measured with scripts/benchmark.py
// (2 runs per setting, order 1-4-4-1) on a laptop, plugged in, in its silent and Turbo power modes.
// Labels live in strings.json.
export const STEPS = ["voice", "render_preview", "qa", "render_final", "stitch"] as const;
export type Step = (typeof STEPS)[number];
export const RENDER_STEPS: Step[] = ["render_preview", "render_final"];
export const MODES = ["silent", "turbo"] as const;
export type Mode = (typeof MODES)[number];
export const SECONDS: Record<Mode, Record<1 | 4, Record<Step, number>>> = {
  silent: {
    1: { voice: 10.3, render_preview: 108.2, qa: 9.7, render_final: 178.8, stitch: 57.9 },
    4: { voice: 10.1, render_preview: 43.8, qa: 9.5, render_final: 81.0, stitch: 59.7 },
  },
  turbo: {
    1: { voice: 8.5, render_preview: 77.7, qa: 7.5, render_final: 127.2, stitch: 47.8 },
    4: { voice: 8.3, render_preview: 34.8, qa: 7.2, render_final: 63.7, stitch: 47.8 },
  },
};

export const sum = (mode: Mode, jobs: 1 | 4, steps: readonly Step[] = STEPS) =>
  steps.reduce((acc, step) => acc + SECONDS[mode][jobs][step], 0);
