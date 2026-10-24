"""Extract QA keyframes, plain and with safe-area / content / subtitle-zone overlays.

Usage:
  qa_frames.py --slug <slug> --lang <lang> [--scenes …] [--preview] [--at-cues]
"""

from __future__ import annotations

import argparse

from _studio import (
    clip_path, fail, main_wrapper, manifest, project_dir, rel, run, select_scenes, theme, timings, tool,
)

BEFORE_END_SEC = 0.45
AFTER_CUE_SEC = 0.5


def ff_color(hex_color: str) -> str:
    return "0x" + hex_color.lstrip("#")


def overlay_filter(th: dict, orientation: str) -> str:
    margin = (1 - th["safe_area"]["ratio"]) / 2
    zones = th["zones"][orientation]
    c = th["colors"]
    content_top = max(zones["content"]["top"], margin)
    content_bottom = min(zones["content"]["bottom"], 1 - margin)
    boxes = [
        # safe area
        (margin, margin, 1 - 2 * margin, 1 - 2 * margin, c["success"], 4),
        # content zone
        (margin, content_top, 1 - 2 * margin, content_bottom - content_top, c["primary"], 2),
        # subtitle zone
        (margin, zones["subtitles"]["top"], 1 - 2 * margin,
         zones["subtitles"]["bottom"] - zones["subtitles"]["top"], c["accent"], 4),
    ]
    return ",".join(
        f"drawbox=x=iw*{x:.4f}:y=ih*{y:.4f}:w=iw*{w:.4f}:h=ih*{h:.4f}:color={ff_color(col)}@0.9:t={t}"
        for x, y, w, h, col, t in boxes
    )


def grab(clip, t: float, out, vf: str | None = None) -> None:
    cmd = [tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", clip, "-frames:v", "1"]
    if vf:
        cmd += ["-vf", vf]
    run(cmd + [out])


def main():
    ap = argparse.ArgumentParser(description="Extract QA keyframes with safe-area and subtitle-zone overlays.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--scenes", nargs="+", help="only these scene ids (default: all)")
    ap.add_argument("--preview", action="store_true", help="use preview renders")
    ap.add_argument("--at-cues", action="store_true", help=f"also grab a frame {AFTER_CUE_SEC}s after each cue")
    args = ap.parse_args()

    man = manifest(args.slug)
    tim = timings(args.slug, args.lang)
    th = theme()
    vf = overlay_filter(th, man.get("orientation", "vertical"))
    out_dir = project_dir(args.slug) / "qa" / args.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = "preview_" if args.preview else ""

    generated = []
    for scene in select_scenes(man, args.scenes):
        sid = scene["id"]
        clip = clip_path(args.slug, args.lang, sid, args.preview)
        if not clip.exists():
            fail(f"{sid}: clip not found: {rel(clip)}; run render.py{' --preview' if args.preview else ''} first")
        st = tim["scenes"][sid]
        total = st["total_frames"] / tim["fps"]
        shots = [("mid", total / 2), ("end", total - BEFORE_END_SEC)]
        if args.at_cues:
            shots += [(f"cue_{name}", cue["sec"] + AFTER_CUE_SEC) for name, cue in st["cues"].items()]
        for label, t in shots:
            t = min(t, total - 1 / tim["fps"])
            plain = out_dir / f"{prefix}{sid}_{label}.png"
            over = out_dir / f"{prefix}{sid}_{label}_overlay.png"
            grab(clip, t, plain)
            grab(clip, t, over, vf)
            generated += [(plain, t), (over, t)]

    for path, t in generated:
        print(f"{rel(path)}  (t={t:.2f}s)")
    print(f"\n{len(generated)} images in {rel(out_dir)}. Overlays: safe area = success, "
          f"content zone = primary, subtitle zone = accent.")


if __name__ == "__main__":
    main_wrapper(main)
