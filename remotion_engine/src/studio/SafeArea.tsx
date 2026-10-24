import React from "react";
import { AbsoluteFill } from "remotion";
import { colors, zoneBoxes } from "./theme";
import type { Orientation } from "./types";

type Box = { top: number; bottom: number; left: number; right: number };

const Outline: React.FC<{ box: Box; color: string }> = ({ box, color }) => (
  <div style={{ position: "absolute", ...box, border: `3px dashed ${color}`, pointerEvents: "none" }} />
);

/** Lays children inside the content zone for the orientation. `debug` draws the zones. */
export const SafeArea: React.FC<{
  orientation: Orientation;
  debug?: boolean;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ orientation, debug, className, style, children }) => {
  const { content, safe, subtitles } = zoneBoxes(orientation);
  return (
    <AbsoluteFill>
      <div
        className={className}
        style={{
          position: "absolute",
          ...content,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          ...style,
        }}
      >
        {children}
      </div>
      {debug ? (
        <>
          <Outline box={safe} color={colors.success} />
          <Outline box={subtitles} color={colors.accent} />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
