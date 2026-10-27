import React from "react";
import { Atom, Dices, Hourglass, Percent, Sparkles, TrendingUp } from "lucide-react";
import { interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCue, useCueProgress } from "@studio/useCue";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** A recap card: dim until `p` reaches 1, then lit in its color. */
const Card: React.FC<{
  p: number;
  color: string;
  icon: React.ReactNode;
  title: string;
  sub: string;
  size: { body: number; caption: number };
}> = ({ p, color, icon, title, sub, size }) => (
  <div
    className="flex flex-col items-center rounded-3xl bg-surface text-center"
    style={{
      width: 440,
      padding: "40px 28px",
      gap: 18,
      border: `4px solid ${interpolateColors(p, [0, 1], [colors.border, color])}`,
      boxShadow: `0 0 ${60 * p}px ${color}44`,
      opacity: 0.3 + 0.7 * p,
      transform: `translateY(${(1 - p) * 24}px)`,
    }}
  >
    <span style={{ color: interpolateColors(p, [0, 1], [colors.textMuted, color]), display: "flex" }}>{icon}</span>
    <div className="font-bold text-text" style={{ fontSize: size.body }}>{title}</div>
    <div className="text-muted" style={{ fontFamily: FONT_MONO, fontSize: size.caption }}>{sub}</div>
  </div>
);

export const Scene06: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;

  const dots = useCueProgress("dots", 18, t);
  const ratio = useCueProgress("ratio", 18, t);
  const samples = useCueProgress("samples", 18, t);
  const uses = useCue("uses", t);
  const chips: [string, React.ReactNode][] = [
    [s["scene_06.physics"], <Atom size={40} />],
    [s["scene_06.finance"], <TrendingUp size={40} />],
    [s["scene_06.graphics"], <Sparkles size={40} />],
  ];

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 70 }}>
        <div className="flex" style={{ gap: 44 }}>
          <Card p={dots} color={colors.primary} icon={<Dices size={64} />} title={s["scene_06.dots"]} sub={s["scene_06.dots_sub"]} size={type} />
          <Card p={ratio} color={colors.accent} icon={<Percent size={64} />} title={s["scene_06.ratio"]} sub={s["scene_06.ratio_sub"]} size={type} />
          <Card p={samples} color={colors.success} icon={<Hourglass size={64} />} title={s["scene_06.samples"]} sub={s["scene_06.samples_sub"]} size={type} />
        </div>
        <div className="flex" style={{ gap: 28 }}>
          {chips.map(([label, icon], i) => {
            const p = interpolate(frame, [uses + i * 10, uses + i * 10 + 16], [0, 1], clamp);
            return (
              <div
                key={label}
                className="flex items-center rounded-full font-semibold text-secondary"
                style={{ gap: 14, padding: "14px 32px", fontSize: type.body, border: `3px solid ${colors.secondary}`, opacity: p, transform: `scale(${0.85 + 0.15 * p})` }}
              >
                {icon}
                {label}
              </div>
            );
          })}
        </div>
      </SafeArea>
    </Fade>
  );
};
