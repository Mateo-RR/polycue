"""Render clean scene clips (no audio, no subtitles) with the engine each scene declares.

Usage:
  render.py --slug <slug> --lang <lang> [--scenes …] [--preview] [--reuse-neutral-from <source_lang>]
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import time
from pathlib import Path

from _studio import (
    MANIM_ENGINE, REMOTION_ENGINE, REPO, clip_path, fail, load_json, locale_dir, main_wrapper,
    manifest, print_table, rel, run, select_scenes, timings, tool, video_info, write_json,
)

PREVIEW_MANIM_FPS = 30


def composition_id(slug: str, scene_id: str) -> str:
    """Mirror of compositionId() in remotion_engine/src/Root.tsx."""
    return f"{slug}--{scene_id}".replace("_", "-").lstrip("-")


def manim_bin() -> Path:
    for candidate in (MANIM_ENGINE / ".venv" / "Scripts" / "manim.exe", MANIM_ENGINE / ".venv" / "bin" / "manim"):
        if candidate.exists():
            return candidate
    fail("manim not found in manim_engine/.venv. See docs/SETUP.md Phase 3.")


def strip_audio(path: Path) -> None:
    if video_info(path)["audio_streams"]:
        tmp = path.with_suffix(".noaudio.mp4")
        run([tool("ffmpeg"), "-y", "-v", "error", "-i", path, "-map", "0:v:0", "-c", "copy", tmp])
        tmp.replace(path)


def render_manim(slug, lang, orientation, scene, preview, dest: Path) -> None:
    scene_file = MANIM_ENGINE / "scenes" / slug / f"{scene['id']}.py"
    if not scene_file.exists():
        fail(f"{scene['id']}: Manim scene file not found: {rel(scene_file)}")
    env = {
        "STUDIO_SLUG": slug,
        "STUDIO_LANG": lang,
        "STUDIO_ORIENTATION": orientation,
        "STUDIO_QUALITY": "preview" if preview else "final",
        "PYTHONPATH": os.pathsep.join([str(MANIM_ENGINE), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
        "PYTHONIOENCODING": "utf-8",
    }
    # The media dir must be on the same drive as the working directory: MiKTeX's
    # dvisvgm fails (Windows API error 87) on cross-drive paths. manim_engine/media/
    # is git-ignored.
    media_root = MANIM_ENGINE / "media"
    media_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render_", dir=media_root) as media:
        run([manim_bin(), "render", scene_file, scene["entry"], "--media_dir", media,
             "--disable_caching", "--progress_bar", "none", "--format", "mp4", "-v", "WARNING"],
            cwd=REPO, env=env)
        outs = [p for p in Path(media).rglob(f"{scene['entry']}.mp4") if "partial_movie_files" not in p.parts]
        if not outs:
            fail(f"{scene['id']}: Manim finished but no {scene['entry']}.mp4 was produced")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(outs[0]), dest)
    strip_audio(dest)


def render_remotion(slug, lang, orientation, scene, scene_timing, strings, preview, dest: Path) -> None:
    props = {"slug": slug, "lang": lang, "orientation": orientation, "timing": scene_timing, "strings": strings}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="remotion_") as tmp:
        props_file = Path(tmp) / "props.json"
        write_json(props_file, props)
        cmd = [tool("npx"), "remotion", "render", "src/index.ts", composition_id(slug, scene["id"]), dest,
               f"--props={props_file}", "--codec=h264", "--pixel-format=yuv420p", "--muted",
               "--log=error"]
        if preview:
            cmd.append("--scale=0.5")
        run(cmd, cwd=REMOTION_ENGINE)


def verify(dest: Path, scene_timing: dict, fps: int, preview: bool) -> tuple[bool, dict]:
    info = video_info(dest)
    if preview:
        clip_sec = info["frames"] / info["fps"]
        ok = abs(clip_sec - scene_timing["total_frames"] / fps) <= 1 / info["fps"] + 1e-6
    else:
        ok = info["frames"] == scene_timing["total_frames"] and round(info["fps"]) == fps
    return ok and info["audio_streams"] == 0, info


def main():
    ap = argparse.ArgumentParser(description="Render clean scene clips with Manim or Remotion per manifest.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--scenes", nargs="+", help="only these scene ids (default: all)")
    ap.add_argument("--preview", action="store_true", help="half resolution (Manim also at 30 fps)")
    ap.add_argument("--reuse-neutral-from", metavar="SOURCE_LANG",
                    help="copy lang_neutral scenes from this language when durations match within one frame")
    args = ap.parse_args()

    man = manifest(args.slug)
    tim = timings(args.slug, args.lang)
    fps = tim["fps"]
    orientation = man.get("orientation", "vertical")
    strings = load_json(locale_dir(args.slug, args.lang) / "strings.json")
    src_tim = timings(args.slug, args.reuse_neutral_from) if args.reuse_neutral_from else None

    rows, failures = [], []
    for scene in select_scenes(man, args.scenes):
        sid = scene["id"]
        if sid not in tim["scenes"]:
            fail(f"{sid} missing in timings.json; run tts_sync.py first")
        st = tim["scenes"][sid]
        dest = clip_path(args.slug, args.lang, sid, args.preview)
        started = time.time()
        action = "rendered"
        reused = False
        if src_tim and scene.get("lang_neutral"):
            src_clip = clip_path(args.slug, args.reuse_neutral_from, sid, args.preview)
            src_frames = src_tim["scenes"].get(sid, {}).get("total_frames")
            if src_clip.exists() and src_frames is not None and abs(src_frames - st["total_frames"]) <= 1:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_clip, dest)
                action, reused = f"reused {args.reuse_neutral_from}", True
        if not reused:
            engine = scene.get("engine")
            print(f"[{sid}] rendering with {engine}{' (preview)' if args.preview else ''} …", flush=True)
            if engine == "manim":
                render_manim(args.slug, args.lang, orientation, scene, args.preview, dest)
            elif engine == "remotion":
                render_remotion(args.slug, args.lang, orientation, scene, st, strings, args.preview, dest)
            else:
                fail(f"{sid}: unknown engine {engine!r} (expected 'manim' or 'remotion')")
        ok, info = verify(dest, st, fps, args.preview)
        expected = st["total_frames"] if not args.preview else f"~{st['total_frames'] / fps:.3f}s"
        rows.append([sid, scene.get("engine"), action, f"{info['width']}x{info['height']}", f"{info['fps']:g}",
                     info["frames"], expected, "OK" if ok else "MISMATCH", f"{time.time() - started:.0f}s"])
        if not ok:
            failures.append(sid)

    print()
    print_table(["scene", "engine", "action", "size", "fps", "frames", "expected", "check", "time"], rows)
    if failures:
        fail(f"frame-count check failed for {failures}")


if __name__ == "__main__":
    main_wrapper(main)
