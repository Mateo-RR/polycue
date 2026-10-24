import type React from "react";
import type { SceneProps } from "../studio/types";

// Built automatically: every `videos/<slug>/SceneNN.tsx` must export a component named `SceneNN`,
// which becomes `scene_NN` of `<slug>` (matching `entry` in the manifest). Other files in a slug
// folder (helpers, shared components) are ignored. No manual registration needed.

type WebpackContext = { keys(): string[]; (key: string): Record<string, unknown> };
const sceneFiles = (require as unknown as {
  context(dir: string, deep: boolean, filter: RegExp): WebpackContext;
}).context("./", true, /^\.\/[^/]+\/Scene\d+\.tsx$/);

export const registry: Record<string, Record<string, React.FC<SceneProps>>> = {};

for (const key of sceneFiles.keys()) {
  const match = /^\.\/([^/]+)\/(Scene(\d+))\.tsx$/.exec(key);
  if (!match) continue;
  const [, slug, entry, number] = match;
  const Component = sceneFiles(key)[entry];
  if (typeof Component !== "function") {
    throw new Error(`videos/${slug}/${entry}.tsx must export a component named ${entry}`);
  }
  (registry[slug] ??= {})[`scene_${number}`] = Component as React.FC<SceneProps>;
}
