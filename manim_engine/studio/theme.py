"""Theme helpers for Manim scenes.

Everything visual comes from ``shared/theme.json``. Scenes import the palette
constants and zone helpers from here instead of hardcoding values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from manim import config, ManimColor

REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_PATH = REPO_ROOT / "shared" / "theme.json"

with THEME_PATH.open(encoding="utf-8") as fh:
    THEME = json.load(fh)

_C = THEME["colors"]
BG = ManimColor(_C["background"])
PRIMARY = ManimColor(_C["primary"])
SECONDARY = ManimColor(_C["secondary"])
ACCENT = ManimColor(_C["accent"])
SUCCESS = ManimColor(_C["success"])
TEXT = ManimColor(_C["text"])
TEXT_MUTED = ManimColor(_C["text_muted"])
SURFACE = ManimColor(_C["surface"])
BORDER = ManimColor(_C["border"])

FONT_SANS = THEME["fonts"]["sans"]
FONT_MONO = THEME["fonts"]["mono"]
FONTS_DIR = REPO_ROOT / THEME["fonts"]["dir"]

FPS_FINAL = int(THEME["fps"])
FPS_PREVIEW = 30

# Manim font_size per CSS pixel of font-size, so a Text matches the cap height
# Remotion gets for the same px value. Measured on the final canvas with
# calibrate() (Inter cap height 0.727 em); identical for both orientations
# because both canvases use 1 frame unit = 135 px.
PX_TO_FONT_SIZE = 0.5333


def orientation() -> str:
    value = os.environ.get("STUDIO_ORIENTATION", "vertical")
    if value not in THEME["canvas"]:
        raise ValueError(f"STUDIO_ORIENTATION must be one of {list(THEME['canvas'])}, got {value!r}")
    return value


def quality() -> str:
    value = os.environ.get("STUDIO_QUALITY", "preview")
    if value not in ("preview", "final"):
        raise ValueError(f"STUDIO_QUALITY must be 'preview' or 'final', got {value!r}")
    return value


def _register_fonts() -> None:
    """Make shared/fonts visible to Pango even if they are not installed system-wide."""
    try:
        import manimpango
    except ImportError:
        return
    installed = set(manimpango.list_fonts())
    if FONT_SANS in installed and FONT_MONO in installed:
        return
    for ttf in sorted(FONTS_DIR.glob("*.ttf")):
        manimpango.register_font(str(ttf))


def configure() -> None:
    """Apply canvas, frame rate and background from the theme to Manim's config."""
    orient = orientation()
    canvas = THEME["canvas"][orient]
    final = quality() == "final"
    scale = 1 if final else 0.5

    config.background_color = BG
    config.frame_rate = FPS_FINAL if final else FPS_PREVIEW
    config.pixel_width = int(canvas["width"] * scale)
    config.pixel_height = int(canvas["height"] * scale)
    if orient == "horizontal":
        config.frame_height = 8.0
        config.frame_width = 8.0 * 16 / 9
    else:
        config.frame_width = 8.0
        config.frame_height = 8.0 * 16 / 9


def _frame_dims() -> tuple[float, float]:
    if orientation() == "horizontal":
        return 8.0 * 16 / 9, 8.0
    return 8.0, 8.0 * 16 / 9


def _frac_to_y(frac_from_top: float) -> float:
    _, fh = _frame_dims()
    return fh / 2 - frac_from_top * fh


def safe_box() -> tuple[float, float, float, float]:
    """(left, right, top, bottom) of the central safe area in frame units."""
    fw, fh = _frame_dims()
    r = THEME["safe_area"]["ratio"]
    return -fw / 2 * r, fw / 2 * r, fh / 2 * r, -fh / 2 * r


def content_box() -> tuple[float, float, float, float]:
    """(left, right, top, bottom) of the content zone, clipped to the safe area."""
    left, right, s_top, s_bottom = safe_box()
    zone = THEME["zones"][orientation()]["content"]
    top = min(s_top, _frac_to_y(zone["top"]))
    bottom = max(s_bottom, _frac_to_y(zone["bottom"]))
    return left, right, top, bottom


def subtitle_box() -> tuple[float, float, float, float]:
    """(left, right, top, bottom) of the reserved subtitle zone."""
    left, right, _, _ = safe_box()
    zone = THEME["zones"][orientation()]["subtitles"]
    return left, right, _frac_to_y(zone["top"]), _frac_to_y(zone["bottom"])


def content_center():
    import numpy as np

    left, right, top, bottom = content_box()
    return np.array([(left + right) / 2, (top + bottom) / 2, 0.0])


def fit_in_content(mobject, margin: float = 0.0):
    """Scale ``mobject`` down (never up) to fit the content zone and center it there."""
    left, right, top, bottom = content_box()
    max_w = right - left - 2 * margin
    max_h = top - bottom - 2 * margin
    factor = min(1.0, max_w / max(mobject.width, 1e-9), max_h / max(mobject.height, 1e-9))
    if factor < 1.0:
        mobject.scale(factor)
    mobject.move_to(content_center())
    return mobject


def px(value: float) -> float:
    """Length in canvas pixels (final resolution) → frame units."""
    _, fh = _frame_dims()
    return value * fh / THEME["canvas"][orientation()]["height"]


def px_to_units(px_size: float) -> float:
    """Font size in CSS pixels (as in theme.json) → Manim ``font_size``."""
    return px_size * PX_TO_FONT_SIZE


def type_size(role: str) -> float:
    """Manim ``font_size`` for a type-scale role (display, title, body, caption)."""
    scale = THEME["type_scale_px"][orientation()]
    if role not in scale:
        raise KeyError(f"Unknown type role {role!r}; available: {list(scale)}")
    return px_to_units(scale[role])


def _inter_cap_ratio() -> float:
    """capHeight / unitsPerEm read from Inter-Regular.ttf (OS/2 and head tables)."""
    import struct

    data = (FONTS_DIR / "Inter-Regular.ttf").read_bytes()
    num_tables = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(num_tables):
        rec = data[12 + 16 * i: 28 + 16 * i]
        tag, _, offset, _ = struct.unpack(">4sIII", rec)
        tables[tag.decode()] = offset
    upm = struct.unpack(">H", data[tables["head"] + 18: tables["head"] + 20])[0]
    cap = struct.unpack(">h", data[tables["OS/2"] + 88: tables["OS/2"] + 90])[0]
    return cap / upm


def calibrate(reference_font_size: float = 100) -> float:
    """Measure the factor stored in PX_TO_FONT_SIZE. Run once after changing fonts."""
    from manim import Text

    configure()
    mob = Text("H", font=FONT_SANS, font_size=reference_font_size)
    _, fh = _frame_dims()
    units_per_px = fh / THEME["canvas"][orientation()]["height"]
    measured_cap_px = mob.height / units_per_px
    return reference_font_size * _inter_cap_ratio() / measured_cap_px


_register_fonts()

__all__ = [
    "THEME", "REPO_ROOT", "BG", "PRIMARY", "SECONDARY", "ACCENT", "SUCCESS", "TEXT",
    "TEXT_MUTED", "SURFACE", "BORDER", "FONT_SANS", "FONT_MONO", "configure",
    "orientation", "quality", "safe_box", "content_box", "subtitle_box", "content_center",
    "fit_in_content", "px", "px_to_units", "type_size",
]
