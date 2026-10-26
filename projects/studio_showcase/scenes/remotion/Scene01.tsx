import React from "react";
import { AudioLines, Clapperboard, FileText, Layers, MessageSquare, Play } from "lucide-react";
import { interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Fade } from "@studio/Fade";
import { FONT_MONO } from "@studio/fonts";
import { SafeArea } from "@studio/SafeArea";
import { colors, fadeInFrames, PADDING_FRAMES, typeScale } from "@studio/theme";
import type { SceneProps } from "@studio/types";
import { useCue, useCueProgress } from "@studio/useCue";

const CARD_W = 340;
const CARD_H = 440;
const LINK_W = 70;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Engine of each block in the mini timeline: true = Manim, false = Remotion.
const TIMELINE = [false, true, true, false, true, false];
const SCRIPT_LINES = [0.92, 0.66, 0.84, 0.54, 0.76];
const CUE_LINES = new Set([1, 3]);
const BARS = 22;

/** A pipeline stage: dim until `p` reaches 1, then lit in its color with a soft glow. */
const Node: React.FC<{
  p: number;
  color: string;
  icon: React.ReactNode;
  label: string;
  sub: string;
  size: { body: number; caption: number };
  children?: React.ReactNode;
}> = ({ p, color, icon, label, sub, size, children }) => (
  <div
    className="flex flex-col rounded-3xl bg-surface"
    style={{
      width: CARD_W,
      height: CARD_H,
      padding: "30px 28px",
      gap: 10,
      border: `4px solid ${interpolateColors(p, [0, 1], [colors.border, color])}`,
      boxShadow: `0 0 ${60 * p}px ${color}44`,
      opacity: 0.35 + 0.65 * p,
      transform: `scale(${0.94 + 0.06 * p})`,
    }}
  >
    <div className="flex items-center font-bold text-text" style={{ gap: 14, fontSize: size.body }}>
      <span style={{ color: interpolateColors(p, [0, 1], [colors.textMuted, color]), display: "flex" }}>{icon}</span>
      {label}
    </div>
    <div className="text-muted" style={{ fontFamily: FONT_MONO, fontSize: size.caption, whiteSpace: "nowrap" }}>{sub}</div>
    <div className="flex flex-col items-center justify-center" style={{ flex: 1, width: "100%" }}>{children}</div>
  </div>
);

/** Connector that fills with `p` while a packet travels along it. */
const Link: React.FC<{ p: number; color: string }> = ({ p, color }) => (
  <div style={{ position: "relative", width: LINK_W, height: 24 }}>
    <div className="rounded-full bg-border" style={{ position: "absolute", left: 0, right: 0, top: 9, height: 6 }} />
    <div className="rounded-full" style={{ position: "absolute", left: 0, top: 9, height: 6, width: LINK_W * p, backgroundColor: color }} />
    <div
      className="rounded-full"
      style={{
        position: "absolute",
        top: 0,
        left: LINK_W * p - 12,
        width: 24,
        height: 24,
        backgroundColor: color,
        boxShadow: `0 0 24px ${color}`,
        opacity: p > 0 && p < 1 ? 1 : 0,
      }}
    />
  </div>
);

export const Scene01: React.FC<SceneProps> = (props) => {
  const frame = useCurrentFrame();
  const type = typeScale(props.orientation);
  const s = props.strings;
  const t = props.timing;

  const cues = { script: useCue("script", t), voice: useCue("voice", t), engines: useCue("engines", t), video: useCue("video", t) };
  const script = useCueProgress("script", 18, t);
  const voice = useCueProgress("voice", 18, t);
  const engines = useCueProgress("engines", 18, t);
  const video = useCueProgress("video", 18, t);
  // Each connector fills just before the stage it leads to lights up.
  const link = (cue: number) => interpolate(frame, [cue - 18, cue + 2], [0, 1], clamp);

  // The request is typed during the opening words; the bar flashes when it is sent.
  const prompt = s["scene_01.prompt"];
  const typed = Math.floor(interpolate(frame, [fadeInFrames, cues.script - 14], [0, prompt.length], clamp));
  const caret = typed < prompt.length || Math.floor(frame / 16) % 2 === 0 ? 1 : 0;
  const sent = interpolate(frame, [cues.script - 8, cues.script + 4, cues.script + 30], [0, 1, 0.35], clamp);

  // Voiceover waveform: flat until the voice stage lights up.
  const bars = Array.from({ length: BARS }, (_, i) => 10 + 120 * voice * (0.18 + 0.82 * Math.abs(Math.sin(frame * 0.21 + i * 0.9) * Math.sin(frame * 0.07 + i * 0.37))));
  // The finished video plays to the end of the narration.
  const playback = interpolate(frame, [cues.video + 10, t.total_frames - PADDING_FRAMES], [0, 1], clamp);

  return (
    <Fade timing={t}>
      <SafeArea orientation={props.orientation} style={{ gap: 72 }}>
        <div
          className="flex items-center rounded-full bg-surface"
          style={{
            width: 1420,
            padding: "26px 40px",
            gap: 24,
            border: `4px solid ${interpolateColors(sent, [0, 1], [colors.border, colors.primary])}`,
            boxShadow: `0 0 ${50 * sent}px ${colors.primary}55`,
          }}
        >
          <div className="flex items-center font-semibold text-primary" style={{ gap: 12, fontSize: type.caption }}>
            <MessageSquare size={38} />
            {s["scene_01.you"]}
          </div>
          <div className="text-text" style={{ fontSize: type.body, whiteSpace: "nowrap" }}>
            {prompt.slice(0, typed)}
            <span className="text-primary" style={{ opacity: caret }}>|</span>
          </div>
        </div>

        <div className="flex items-center">
          <Node p={script} color={colors.accent} icon={<FileText size={44} />} label={s["scene_01.script"]} sub={s["scene_01.script_sub"]} size={type}>
            <div className="flex flex-col" style={{ width: "100%", gap: 18 }}>
              {SCRIPT_LINES.map((w, i) => {
                const lp = interpolate(frame, [cues.script + i * 6, cues.script + i * 6 + 12], [0, 1], clamp);
                return (
                  <div key={i} className="flex items-center" style={{ gap: 10, width: `${100 * w * lp}%`, opacity: lp }}>
                    {CUE_LINES.has(i) ? <div className="rounded-full" style={{ width: 44, height: 16, flexShrink: 0, backgroundColor: colors.accent }} /> : null}
                    <div className="rounded-full" style={{ flex: 1, height: 16, backgroundColor: colors.textMuted, opacity: 0.45 }} />
                  </div>
                );
              })}
            </div>
          </Node>
          <Link p={link(cues.voice)} color={colors.success} />
          <Node p={voice} color={colors.success} icon={<AudioLines size={44} />} label={s["scene_01.voice"]} sub={s["scene_01.voice_sub"]} size={type}>
            <div className="flex items-center" style={{ gap: 5, height: 150 }}>
              {bars.map((h, i) => (
                <div key={i} className="rounded-full" style={{ width: 7, height: h, backgroundColor: interpolateColors(voice, [0, 1], [colors.border, colors.success]) }} />
              ))}
            </div>
          </Node>
          <Link p={link(cues.engines)} color={colors.secondary} />
          <Node p={engines} color={colors.secondary} icon={<Layers size={44} />} label={s["scene_01.scenes"]} sub={s["scene_01.scenes_sub"]} size={type}>
            <div className="flex flex-col items-center" style={{ gap: 26 }}>
              <div className="flex" style={{ gap: 12 }}>
                {[
                  [s["scene_01.manim"], colors.secondary],
                  [s["scene_01.remotion"], colors.primary],
                ].map(([name, color]) => (
                  <div key={name} className="rounded-full font-semibold" style={{ border: `3px solid ${color}`, color, fontSize: type.caption, padding: "6px 18px", opacity: 0.3 + 0.7 * engines }}>
                    {name}
                  </div>
                ))}
              </div>
              <div className="flex" style={{ gap: 8 }}>
                {TIMELINE.map((isManim, i) => {
                  const bp = interpolate(frame, [cues.engines + 8 + i * 7, cues.engines + 20 + i * 7], [0, 1], clamp);
                  return (
                    <div
                      key={i}
                      className="rounded-lg"
                      style={{ width: 38, height: 58, backgroundColor: interpolateColors(bp, [0, 1], [colors.border, isManim ? colors.secondary : colors.primary]), transform: `translateY(${(1 - bp) * 14}px)` }}
                    />
                  );
                })}
              </div>
            </div>
          </Node>
          <Link p={link(cues.video)} color={colors.primary} />
          <Node p={video} color={colors.primary} icon={<Clapperboard size={44} />} label={s["scene_01.video"]} sub={s["scene_01.video_sub"]} size={type}>
            <div className="flex flex-col rounded-2xl" style={{ width: 268, height: 151, border: `3px solid ${interpolateColors(video, [0, 1], [colors.border, colors.primary])}`, backgroundColor: colors.bg, overflow: "hidden" }}>
              <div className="flex" style={{ height: 10, opacity: video }}>
                {TIMELINE.map((isManim, i) => (
                  <div key={i} style={{ flex: 1, backgroundColor: isManim ? colors.secondary : colors.primary }} />
                ))}
              </div>
              <div className="flex items-center justify-center" style={{ flex: 1 }}>
                <div style={{ transform: `scale(${0.4 + 0.6 * video})`, opacity: video, display: "flex" }}>
                  <Play size={60} color={colors.text} fill={colors.text} />
                </div>
              </div>
              <div style={{ height: 8, backgroundColor: colors.border }}>
                <div style={{ height: 8, width: `${100 * playback}%`, backgroundColor: colors.primary }} />
              </div>
            </div>
          </Node>
        </div>
      </SafeArea>
    </Fade>
  );
};
