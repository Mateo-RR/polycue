import "./index.css";
import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { canvas, FPS, PADDING_FRAMES } from "./studio/theme";
import type { SceneProps } from "./studio/types";
import { registry } from "./registry";

/**
 * Remotion ids allow only letters, digits and hyphens. Leading hyphens are stripped because
 * the CLI would parse the id as a flag. Mirrored in scripts/render.py.
 */
export const compositionId = (slug: string, sceneId: string) =>
  `${slug}--${sceneId}`.replace(/_/g, "-").replace(/^-+/, "");

const placeholderProps = (slug: string): SceneProps => ({
  slug,
  lang: "es-ES",
  orientation: "vertical",
  strings: {},
  timing: {
    duration_sec: 4,
    duration_frames: 4 * FPS,
    total_frames: 4 * FPS + PADDING_FRAMES,
    total_sec: (4 * FPS + PADDING_FRAMES) / FPS,
    cues: {},
    placeholder: true,
  },
});

const calculateMetadata: CalculateMetadataFunction<SceneProps> = ({ props }) => {
  const { width, height } = canvas(props.orientation);
  return { durationInFrames: props.timing.total_frames, width, height, fps: FPS };
};

export const Root: React.FC = () => (
  <>
    {Object.entries(registry).flatMap(([slug, scenes]) =>
      Object.entries(scenes).map(([sceneId, Component]) => {
        const defaults = placeholderProps(slug);
        const { width, height } = canvas(defaults.orientation);
        return (
          <Composition
            key={`${slug}/${sceneId}`}
            id={compositionId(slug, sceneId)}
            component={Component}
            fps={FPS}
            width={width}
            height={height}
            durationInFrames={defaults.timing.total_frames}
            defaultProps={defaults}
            calculateMetadata={calculateMetadata}
          />
        );
      }),
    )}
  </>
);
