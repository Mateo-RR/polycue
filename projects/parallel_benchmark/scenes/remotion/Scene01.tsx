import React from "react";
import { interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCue, useCueProgress } from "@studio/useCue";
import { MODES, type Mode, RENDER_STEPS, SECONDS, STEPS } from "./data";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const LABEL_W = 225;
const BAR_MAX = 270; // width of the longest bar, shared by both panels so they compare
const BAR_H = 16;
const ROW_H = 30; // one bar and its value; taller than the bar so stacked values never touch
const WIDTH = 1540; // both panels, inside the content zone
const MAX = Math.max(...MODES.flatMap((m) => STEPS.map((s) => SECONDS[m][1][s])));

export const Scene01: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;
  const num = new Intl.NumberFormat(props.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  const steps = useCue("steps", t);
  const render = useCueProgress("render", 18, t);
  const intro = interpolate(frame, [fadeInFrames, fadeInFrames + 20], [0, 1], clamp);

  const bar = (value: number, color: string, p: number, dim: number) => (
    <div className="flex items-center" style={{ gap: 10, height: ROW_H }}>
      <div className="rounded-full" style={{ width: Math.max(6, (BAR_MAX * value * p) / MAX), height: BAR_H, backgroundColor: color, opacity: dim }} />
      <div style={{ fontFamily: FONT_MONO, fontSize: type.caption, color: colors.text, opacity: p * dim, whiteSpace: "nowrap" }}>
        {s["scene_01.seconds"].replace("{value}", num.format(value))}
      </div>
    </div>
  );

  const panel = (mode: Mode, delay: number) => (
    <div className="flex flex-col rounded-3xl bg-surface" style={{ flex: 1, gap: 14, padding: "22px 24px", border: `3px solid ${colors.border}` }}>
      <div className="font-bold text-text" style={{ fontSize: type.body }}>{s[`scene_01.${mode}`]}</div>
      {STEPS.map((step, i) => {
        // Rows grow one after another from the "steps" cue; the second panel starts a little later.
        const start = steps + delay + i * 7;
        const p = interpolate(frame, [start, start + 28], [0, 1], { ...clamp, easing: (x) => 1 - (1 - x) ** 3 });
        const isRender = RENDER_STEPS.includes(step);
        const dim = isRender ? 1 : 1 - 0.55 * render;
        const speedup = SECONDS[mode][1][step] / SECONDS[mode][4][step];
        return (
          <div key={step} className="flex items-center" style={{ opacity: Math.min(1, p * 2) }}>
            <div
              className="font-semibold"
              style={{ width: LABEL_W, fontSize: type.caption, color: isRender ? interpolateColors(render, [0, 1], [colors.text, colors.accent]) : colors.text, opacity: dim }}
            >
              {s[`scene_01.${step}`]}
            </div>
            <div className="flex flex-col" style={{ width: BAR_MAX + 110 }}>
              {bar(SECONDS[mode][1][step], colors.textMuted, p, dim)}
              {bar(SECONDS[mode][4][step], colors.primary, p, dim)}
            </div>
            <div
              className="rounded-full font-bold text-accent"
              style={{ fontFamily: FONT_MONO, fontSize: type.caption, padding: "4px 14px", border: `3px solid ${colors.accent}`, opacity: isRender ? render : 0 }}
            >
              {s["scene_01.speedup"].replace("{value}", num.format(speedup))}
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 30 }}>
        <div className="flex items-end justify-between" style={{ width: WIDTH, opacity: intro }}>
          <div className="flex flex-col" style={{ gap: 6 }}>
            <div className="font-bold text-text" style={{ fontSize: type.title }}>{s["scene_01.title"]}</div>
            <div className="text-muted" style={{ fontFamily: FONT_MONO, fontSize: type.caption }}>{s["scene_01.video"]}</div>
          </div>
          <div className="flex" style={{ gap: 28, fontSize: type.caption }}>
            {[
              [s["scene_01.jobs_1"], colors.textMuted],
              [s["scene_01.jobs_4"], colors.primary],
            ].map(([label, color]) => (
              <div key={label} className="flex items-center text-text" style={{ gap: 12 }}>
                <div className="rounded-full" style={{ width: 34, height: 16, backgroundColor: color }} />
                {label}
              </div>
            ))}
          </div>
        </div>
        <div className="flex" style={{ gap: 24, width: WIDTH }}>
          {panel("silent", 0)}
          {panel("turbo", 20)}
        </div>
      </SafeArea>
    </Fade>
  );
};
