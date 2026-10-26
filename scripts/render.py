"""Render clean scene clips (no audio, no subtitles) with the engine each scene declares.

Scenes render in parallel: up to --jobs at a time, with at most one Remotion scene among them
(a single Remotion render already uses several cores; Manim uses about one per scene).
Remotion scenes share one bundle, built once per run.

Usage:
  render.py --slug <slug> --lang <lang> [--scenes …] [--preview] [--jobs N] [--reuse-neutral-from <source_lang>]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _studio import (
    MANIM_ENGINE, REMOTION_ENGINE, REPO, StudioError, clip_path, fail, load_json, locale_dir, main_wrapper,
    manifest, print_table, project_dir, rel, run, select_scenes, timings, tool, video_info, write_json,
)

PREVIEW_MANIM_FPS = 30
ENGINES = ("manim", "remotion")


def default_jobs() -> int:
    return max(1, (os.cpu_count() or 2) // 2)


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
    scene_file = project_dir(slug) / "scenes" / "manim" / f"{scene['id']}.py"
    if not scene_file.exists():
        fail(f"{scene['id']}: Manim scene file not found: {rel(scene_file)}")
    # The scene folder is on the path so scenes can import their helpers (`from common import …`).
    path = [str(scene_file.parent), str(MANIM_ENGINE), os.environ.get("PYTHONPATH", "")]
    env = {
        "STUDIO_SLUG": slug,
        "STUDIO_LANG": lang,
        "STUDIO_ORIENTATION": orientation,
        "STUDIO_QUALITY": "preview" if preview else "final",
        "PYTHONPATH": os.pathsep.join(path).rstrip(os.pathsep),
        "PYTHONIOENCODING": "utf-8",
    }
    # The media dir must be on the same drive as the working directory: MiKTeX's
    # dvisvgm fails (Windows API error 87) on cross-drive paths. manim_engine/media/
    # is git-ignored. Each render gets its own media dir (LaTeX cache included), so
    # parallel renders never write to the same files.
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


def bundle_remotion(out_dir: Path) -> Path:
    """Build the Remotion project once; every Remotion render of the run uses this bundle."""
    run([tool("npx"), "remotion", "bundle", "src/index.ts", f"--out-dir={out_dir}", "--log=error"],
        cwd=REMOTION_ENGINE)
    return out_dir


def render_remotion(bundle: Path, slug, lang, orientation, scene, scene_timing, strings, preview, dest: Path) -> None:
    props = {"slug": slug, "lang": lang, "orientation": orientation, "timing": scene_timing, "strings": strings}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="remotion_") as tmp:
        props_file = Path(tmp) / "props.json"
        write_json(props_file, props)
        cmd = [tool("npx"), "remotion", "render", bundle, composition_id(slug, scene["id"]), dest,
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
    ap.add_argument("--jobs", type=int, default=default_jobs(),
                    help="scenes rendered at the same time, at most one of them Remotion "
                         "(default: half the CPU cores, here %(default)s)")
    ap.add_argument("--reuse-neutral-from", metavar="SOURCE_LANG",
                    help="copy lang_neutral scenes from this language when durations match within one frame")
    args = ap.parse_args()
    if args.jobs < 1:
        fail("--jobs must be at least 1")

    man = manifest(args.slug)
    tim = timings(args.slug, args.lang)
    fps = tim["fps"]
    orientation = man.get("orientation", "vertical")
    strings = load_json(locale_dir(args.slug, args.lang) / "strings.json")
    src_tim = timings(args.slug, args.reuse_neutral_from) if args.reuse_neutral_from else None

    scenes = select_scenes(man, args.scenes)
    for scene in scenes:
        if scene["id"] not in tim["scenes"]:
            fail(f"{scene['id']} missing in timings.json; run tts_sync.py first")
        if scene.get("engine") not in ENGINES:
            fail(f"{scene['id']}: unknown engine {scene.get('engine')!r} (expected 'manim' or 'remotion')")

    actions, to_render = {}, []
    for scene in scenes:
        sid = scene["id"]
        if src_tim and scene.get("lang_neutral"):
            src_clip = clip_path(args.slug, args.reuse_neutral_from, sid, args.preview)
            src_frames = src_tim["scenes"].get(sid, {}).get("total_frames")
            if src_clip.exists() and src_frames is not None and abs(src_frames - tim["scenes"][sid]["total_frames"]) <= 1:
                dest = clip_path(args.slug, args.lang, sid, args.preview)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_clip, dest)
                actions[sid] = (f"reused {args.reuse_neutral_from}", 0.0)
                continue
        to_render.append(scene)

    errors = {}
    with tempfile.TemporaryDirectory(prefix="remotion_bundle_") as tmp:
        bundle = None
        if any(s["engine"] == "remotion" for s in to_render):
            print("Bundling the Remotion project …", flush=True)
            bundle = bundle_remotion(Path(tmp) / "bundle")

        def render_one(scene: dict) -> None:
            sid = scene["id"]
            dest = clip_path(args.slug, args.lang, sid, args.preview)
            print(f"[{sid}] rendering with {scene['engine']}{' (preview)' if args.preview else ''} …", flush=True)
            started = time.time()
            try:
                if scene["engine"] == "manim":
                    render_manim(args.slug, args.lang, orientation, scene, args.preview, dest)
                else:
                    render_remotion(bundle, args.slug, args.lang, orientation, scene, tim["scenes"][sid], strings,
                                    args.preview, dest)
            except StudioError as exc:
                errors[sid] = str(exc)
                print(f"[{sid}] FAILED", flush=True)
                return
            actions[sid] = ("rendered", time.time() - started)
            print(f"[{sid}] done in {time.time() - started:.0f}s", flush=True)

        # Remotion scenes queue on a single worker; Manim scenes share the remaining jobs.
        # With --jobs 1 everything runs one after another on the same worker.
        remotion = [s for s in to_render if s["engine"] == "remotion"]
        manim = [s for s in to_render if s["engine"] == "manim"]
        manim_workers = args.jobs - 1 if remotion and args.jobs > 1 else args.jobs
        with ThreadPoolExecutor(1) as remotion_pool, ThreadPoolExecutor(manim_workers) as manim_pool:
            remotion_queue = remotion_pool if args.jobs > 1 else manim_pool
            futures = [remotion_queue.submit(render_one, s) for s in remotion]
            futures += [manim_pool.submit(render_one, s) for s in manim]
            for future in futures:
                future.result()

    rows, mismatches = [], []
    for scene in scenes:
        sid, st = scene["id"], tim["scenes"][scene["id"]]
        if sid in errors:
            rows.append([sid, scene["engine"], "FAILED", "", "", "", "", "", ""])
            continue
        action, seconds = actions[sid]
        ok, info = verify(clip_path(args.slug, args.lang, sid, args.preview), st, fps, args.preview)
        expected = st["total_frames"] if not args.preview else f"~{st['total_frames'] / fps:.3f}s"
        rows.append([sid, scene["engine"], action, f"{info['width']}x{info['height']}", f"{info['fps']:g}",
                     info["frames"], expected, "OK" if ok else "MISMATCH", f"{seconds:.0f}s"])
        if not ok:
            mismatches.append(sid)

    print()
    print_table(["scene", "engine", "action", "size", "fps", "frames", "expected", "check", "time"], rows)
    problems = [f"{sid}: {message}" for sid, message in errors.items()]
    if mismatches:
        problems.append(f"frame-count check failed for {mismatches}")
    if problems:
        sys.stdout.flush()  # table before the error, even when the output is piped
        fail("\n\n".join(problems))


if __name__ == "__main__":
    main_wrapper(main)
