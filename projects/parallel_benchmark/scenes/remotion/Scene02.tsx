import React from "react";
import { CheckCircle2, Cpu, Gauge, Laptop, MemoryStick, Plug, Timer } from "lucide-react";
import { interpolate, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCueProgress } from "@studio/useCue";
import { type Mode, RENDER_STEPS, sum } from "./data";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** One power mode: how much faster 4 jobs made rendering and the whole pipeline. */
const ModeCard: React.FC<{
  p: number;
  color: string;
  title: string;
  rows: { icon: React.ReactNode; label: string; value: string; detail: string }[];
  size: { title: number; body: number; caption: number };
}> = ({ p, color, title, rows, size }) => (
  <div
    className="flex flex-col rounded-3xl bg-surface"
    style={{
      width: 700,
      padding: "32px 40px",
      gap: 22,
      border: `4px solid ${color}`,
      boxShadow: `0 0 ${70 * p}px ${color}44`,
      opacity: p,
      transform: `translateY(${(1 - p) * 30}px)`,
    }}
  >
    <div className="font-bold" style={{ fontSize: size.body, color }}>{title}</div>
    {rows.map((row) => (
      <div key={row.label} className="flex items-center justify-between">
        <div className="flex flex-col" style={{ gap: 4 }}>
          <div className="flex items-center font-semibold text-text" style={{ gap: 12, fontSize: size.body }}>
            <span style={{ color, display: "flex" }}>{row.icon}</span>
            {row.label}
          </div>
          <div className="text-muted" style={{ fontFamily: FONT_MONO, fontSize: size.caption }}>{row.detail}</div>
        </div>
        <div className="font-bold" style={{ fontSize: size.title, color }}>{row.value}</div>
      </div>
    ))}
  </div>
);

export const Scene02: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;
  const one = new Intl.NumberFormat(props.lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const whole = new Intl.NumberFormat(props.lang, { maximumFractionDigits: 0 });

  const silent = useCueProgress("silent", 20, t);
  const turbo = useCueProgress("turbo", 20, t);
  const same = useCueProgress("same", 18, t);
  const specs = interpolate(frame, [fadeInFrames, fadeInFrames + 20], [0, 1], clamp);

  const row = (icon: React.ReactNode, key: string, before: number, after: number) => ({
    icon,
    label: s[`scene_02.${key}`],
    value: s["scene_02.speedup"].replace("{value}", one.format(before / after)),
    detail: s["scene_02.before_after"].replace("{before}", whole.format(before)).replace("{after}", whole.format(after)),
  });
  const rows = (mode: Mode) => [
    row(<Timer size={36} />, "render", sum(mode, 1, RENDER_STEPS), sum(mode, 4, RENDER_STEPS)),
    row(<Gauge size={36} />, "total", sum(mode, 1), sum(mode, 4)),
  ];
  const chips: [React.ReactNode, string][] = [
    [<Laptop size={32} />, s["scene_02.laptop"]],
    [<Cpu size={32} />, s["scene_02.cpu"]],
    [<MemoryStick size={32} />, s["scene_02.ram"]],
    [<Plug size={32} />, s["scene_02.power"]],
    [<Gauge size={32} />, s["scene_02.gpu"]],
  ];

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 36 }}>
        <div className="flex" style={{ gap: 48 }}>
          <ModeCard p={silent} color={colors.secondary} title={s["scene_02.silent"]} rows={rows("silent")} size={type} />
          <ModeCard p={turbo} color={colors.accent} title={s["scene_02.turbo"]} rows={rows("turbo")} size={type} />
        </div>
        <div className="flex items-center font-semibold text-success" style={{ gap: 14, fontSize: type.body, opacity: same, transform: `scale(${0.9 + 0.1 * same})` }}>
          <CheckCircle2 size={40} />
          {s["scene_02.same"]}
        </div>
        <div className="flex flex-wrap justify-center" style={{ gap: 16, opacity: specs, maxWidth: 1500 }}>
          {chips.map(([icon, label]) => (
            <div
              key={label}
              className="flex items-center rounded-full text-muted"
              style={{ gap: 12, padding: "8px 22px", fontSize: type.caption, border: `2px solid ${colors.border}`, fontFamily: FONT_MONO }}
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
