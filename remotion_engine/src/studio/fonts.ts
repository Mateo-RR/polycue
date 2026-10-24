import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

// "greek" so math symbols in strings (μ, σ, θ, χ…) render in the theme fonts instead of a serif fallback.
export const { fontFamily: FONT_SANS } = loadInter("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin", "latin-ext", "greek"],
});

export const { fontFamily: FONT_MONO } = loadJetBrainsMono("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin", "latin-ext", "greek"],
});
