// Average seconds per pipeline step for projects/monte_carlo_pi (2 runs per setting, order 1-4-4-1).
// Generated from the benchmark results; labels live in strings.json.
export const STEPS = ["voice", "render_preview", "qa", "render_final", "stitch"] as const;
export type Step = (typeof STEPS)[number];
export const RENDER_STEPS: Step[] = ["render_preview", "render_final"];
export const SECONDS: Record<1 | 4, Record<Step, number>> = {
  1: { voice: 10.3, render_preview: 108.2, qa: 9.7, render_final: 178.8, stitch: 57.9 },
  4: { voice: 10.1, render_preview: 43.8, qa: 9.5, render_final: 81.0, stitch: 59.7 },
};
