import React from "react";
import { interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCue, useCueProgress } from "@studio/useCue";
import { RENDER_STEPS, SECONDS, STEPS } from "./data";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const LABEL_W = 330;
const BAR_MAX = 960; // width of the longest bar (the slowest step with 1 job)
const BAR_H = 30;
const MAX = Math.max(...STEPS.map((s) => SECONDS[1][s]));

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
    <div className="flex items-center" style={{ gap: 14, height: BAR_H }}>
      <div className="rounded-full" style={{ width: Math.max(6, (BAR_MAX * value * p) / MAX), height: BAR_H, backgroundColor: color, opacity: dim }} />
      <div style={{ fontFamily: FONT_MONO, fontSize: type.caption, color: colors.text, opacity: p * dim, whiteSpace: "nowrap" }}>
        {s["scene_01.seconds"].replace("{value}", num.format(value))}
      </div>
    </div>
  );

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 40 }}>
        <div className="flex items-end justify-between" style={{ width: LABEL_W + BAR_MAX + 300, opacity: intro }}>
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

        <div className="flex flex-col" style={{ gap: 26 }}>
          {STEPS.map((step, i) => {
            // Rows grow one after another from the "steps" cue.
            const p = interpolate(frame, [steps + i * 9, steps + i * 9 + 30], [0, 1], { ...clamp, easing: (x) => 1 - (1 - x) ** 3 });
            const isRender = RENDER_STEPS.includes(step);
            const dim = isRender ? 1 : 1 - 0.55 * render;
            const speedup = SECONDS[1][step] / SECONDS[4][step];
            return (
              <div key={step} className="flex items-center" style={{ opacity: Math.min(1, p * 2) }}>
                <div
                  className="font-semibold"
                  style={{ width: LABEL_W, fontSize: type.body, color: isRender ? interpolateColors(render, [0, 1], [colors.text, colors.accent]) : colors.text, opacity: dim }}
                >
                  {s[`scene_01.${step}`]}
                </div>
                <div className="flex flex-col" style={{ gap: 8, width: BAR_MAX + 160 }}>
                  {bar(SECONDS[1][step], colors.textMuted, p, dim)}
                  {bar(SECONDS[4][step], colors.primary, p, dim)}
                </div>
                <div
                  className="rounded-full font-bold text-accent"
                  style={{
                    fontFamily: FONT_MONO,
                    fontSize: type.body,
                    padding: "6px 20px",
                    border: `3px solid ${colors.accent}`,
                    opacity: isRender ? render : 0,
                    transform: `scale(${0.8 + 0.2 * render})`,
                  }}
                >
                  {s["scene_01.speedup"].replace("{value}", num.format(speedup))}
                </div>
              </div>
            );
          })}
        </div>
      </SafeArea>
    </Fade>
  );
};
