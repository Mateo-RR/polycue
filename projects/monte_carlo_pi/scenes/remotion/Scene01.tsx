import React from "react";
import { Dices } from "lucide-react";
import { interpolate, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCue, useCueProgress } from "@studio/useCue";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const N_DOTS = 160;

// Deterministic pseudo-random backdrop: the same dots on every render.
const rand = (i: number) => {
  const x = Math.sin(i * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};
const DOTS = Array.from({ length: N_DOTS }, (_, i) => ({ x: rand(i), y: rand(i + 1000), delay: rand(i + 2000) }));

export const Scene01: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;

  const pi = useCue("pi", t);
  const method = useCueProgress("method", 18, t);
  const words = s["scene_01.question"].split(" ");

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 64 }}>
        {/* Dots rain softly into the content zone, inside the circle in sky, outside in purple. */}
        <div style={{ position: "absolute", inset: 0 }}>
          {DOTS.map((d, i) => {
            const start = fadeInFrames + d.delay * (pi + 120);
            const p = interpolate(frame, [start, start + 20], [0, 1], clamp);
            const inCircle = (d.x - 0.5) ** 2 * (16 / 9) ** 2 + (d.y - 0.5) ** 2 <= 0.25;
            return (
              <div
                key={i}
                className="rounded-full"
                style={{
                  position: "absolute",
                  left: `${d.x * 100}%`,
                  top: `${d.y * 100}%`,
                  width: 12,
                  height: 12,
                  backgroundColor: inCircle ? colors.primary : colors.secondary,
                  opacity: 0.28 * p,
                  transform: `translateY(${(1 - p) * -30}px)`,
                }}
              />
            );
          })}
        </div>

        <div className="flex flex-wrap justify-center font-bold text-text" style={{ fontSize: type.display, gap: "0 0.28em", maxWidth: 1500 }}>
          {words.map((w, i) => {
            const p = interpolate(frame, [pi + i * 5, pi + i * 5 + 16], [0, 1], clamp);
            const isPi = w.includes("π");
            return (
              <span key={i} style={{ opacity: p, transform: `translateY(${(1 - p) * 40}px)`, color: isPi ? colors.accent : undefined, display: "inline-block" }}>
                {w}
              </span>
            );
          })}
        </div>

        <div
          className="flex items-center rounded-full bg-surface font-semibold text-accent"
          style={{
            gap: 20,
            padding: "22px 44px",
            fontSize: type.body,
            border: `4px solid ${colors.accent}`,
            boxShadow: `0 0 ${50 * method}px ${colors.accent}55`,
            opacity: method,
            transform: `scale(${0.9 + 0.1 * method})`,
          }}
        >
          <Dices size={52} />
          {s["scene_01.method"]}
        </div>
      </SafeArea>
    </Fade>
  );
};
