// Tailwind theme extended from shared/theme.json (single source of truth).
const theme = require("../shared/theme.json");
const c = theme.colors;

module.exports = {
  theme: {
    extend: {
      colors: {
        bg: c.background,
        primary: c.primary,
        secondary: c.secondary,
        accent: c.accent,
        success: c.success,
        text: c.text,
        muted: c.text_muted,
        surface: c.surface,
        border: c.border,
      },
      fontFamily: {
        sans: [theme.fonts.sans, ...theme.fonts.fallback, "sans-serif"],
        mono: [theme.fonts.mono, "monospace"],
      },
    },
  },
};
