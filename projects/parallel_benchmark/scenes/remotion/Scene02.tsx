import React from "react";
import { CheckCircle2, Cpu, Gauge, MemoryStick, Monitor, Timer } from "lucide-react";
import { interpolate, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCueProgress } from "@studio/useCue";
import { RENDER_STEPS, SECONDS, STEPS } from "./data";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const sum = (jobs: 1 | 4, steps: readonly (typeof STEPS)[number][]) => steps.reduce((acc, step) => acc + SECONDS[jobs][step], 0);

/** A big result card: icon, label, speed-up and the seconds behind it. */
const Stat: React.FC<{
  p: number;
  color: string;
  icon: React.ReactNode;
  label: string;
  value: string;
  faster: string;
  detail: string;
  size: { title: number; body: number; caption: number; display: number };
}> = ({ p, color, icon, label, value, faster, detail, size }) => (
  <div
    className="flex flex-col items-center rounded-3xl bg-surface"
    style={{
      width: 620,
      padding: "40px 32px",
      gap: 14,
      border: `4px solid ${color}`,
      boxShadow: `0 0 ${70 * p}px ${color}44`,
      opacity: p,
      transform: `translateY(${(1 - p) * 30}px)`,
    }}
  >
    <div className="flex items-center font-semibold text-text" style={{ gap: 14, fontSize: size.body }}>
      <span style={{ color, display: "flex" }}>{icon}</span>
      {label}
    </div>
    <div className="flex items-baseline" style={{ gap: 18, color }}>
      <span className="font-bold" style={{ fontSize: size.display, lineHeight: 1 }}>{value}</span>
      <span className="font-semibold" style={{ fontSize: size.title }}>{faster}</span>
    </div>
    <div className="text-muted" style={{ fontFamily: FONT_MONO, fontSize: size.caption }}>{detail}</div>
  </div>
);

export const Scene02: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;
  const one = new Intl.NumberFormat(props.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const whole = new Intl.NumberFormat(props.lang, { maximumFractionDigits: 0 });

  const render = useCueProgress("render", 20, t);
  const total = useCueProgress("total", 20, t);
  const same = useCueProgress("same", 18, t);
  const specs = interpolate(frame, [fadeInFrames, fadeInFrames + 20], [0, 1], clamp);

  const stat = (before: number, after: number) => ({
    value: s["scene_02.speedup"].replace("{value}", one.format(before / after)),
    faster: s["scene_02.faster"],
    detail: s["scene_02.before_after"].replace("{before}", whole.format(before)).replace("{after}", whole.format(after)),
  });
  const renderStat = stat(sum(1, RENDER_STEPS), sum(4, RENDER_STEPS));
  const totalStat = stat(sum(1, STEPS), sum(4, STEPS));
  const chips: [React.ReactNode, string][] = [
    [<Cpu size={34} />, s["scene_02.cpu"]],
    [<MemoryStick size={34} />, s["scene_02.ram"]],
    [<Monitor size={34} />, s["scene_02.os"]],
    [<Gauge size={34} />, s["scene_02.gpu"]],
  ];

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 44 }}>
        <div className="flex" style={{ gap: 56 }}>
          <Stat p={render} color={colors.accent} icon={<Timer size={44} />} label={s["scene_02.render"]} size={type} {...renderStat} />
          <Stat p={total} color={colors.primary} icon={<Gauge size={44} />} label={s["scene_02.total"]} size={type} {...totalStat} />
        </div>
        <div
          className="flex items-center font-semibold text-success"
          style={{ gap: 14, fontSize: type.body, opacity: same, transform: `scale(${0.9 + 0.1 * same})` }}
        >
          <CheckCircle2 size={40} />
          {s["scene_02.same"]}
        </div>
        <div className="flex flex-wrap justify-center" style={{ gap: 18, opacity: specs, maxWidth: 1150 }}>
          {chips.map(([icon, label]) => (
            <div
              key={label}
              className="flex items-center rounded-full text-muted"
              style={{ gap: 12, padding: "10px 24px", fontSize: type.caption, border: `2px solid ${colors.border}`, fontFamily: FONT_MONO }}
            >
              {icon}
              {label}
            </div>
          ))}
        </div>
      </SafeArea>
    </Fade>
  );
};
