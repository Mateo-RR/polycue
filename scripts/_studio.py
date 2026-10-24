"""Shared helpers for the studio scripts (paths, JSON, manifest, ffmpeg/ffprobe)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARED = REPO / "shared"
MANIM_ENGINE = REPO / "manim_engine"
REMOTION_ENGINE = REPO / "remotion_engine"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


class StudioError(Exception):
    """An expected failure with a message meant for the user."""


def fail(message: str) -> None:
    raise StudioError(message)


def main_wrapper(main) -> None:
    try:
        main()
    except StudioError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"file not found: {rel(path)}")
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {rel(path)}: {exc}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path)


def theme() -> dict:
    return load_json(SHARED / "theme.json")


def voices() -> dict:
    return load_json(SHARED / "voices.json")


def project_dir(slug: str) -> Path:
    d = REPO / "projects" / slug
    if not d.exists():
        fail(f"project not found: {rel(d)}")
    return d


def manifest(slug: str) -> dict:
    return load_json(project_dir(slug) / "manifest.json")


def locale_dir(slug: str, lang: str) -> Path:
    return project_dir(slug) / "locales" / lang


def timings(slug: str, lang: str) -> dict:
    path = locale_dir(slug, lang) / "timings.json"
    if not path.exists():
        fail(f"{rel(path)} not found. Run scripts/tts_sync.py --slug {slug} --lang {lang} first.")
    return load_json(path)


def select_scenes(man: dict, wanted: list[str] | None) -> list[dict]:
    scenes = man["scenes"]
    if not wanted:
        return scenes
    ids = [s["id"] for s in scenes]
    unknown = [w for w in wanted if w not in ids]
    if unknown:
        fail(f"unknown scene(s) {unknown}; manifest has {ids}")
    return [s for s in scenes if s["id"] in wanted]


def clip_path(slug: str, lang: str, scene_id: str, preview: bool) -> Path:
    base = project_dir(slug) / "renders" / lang
    return (base / "preview" if preview else base) / f"{scene_id}.mp4"


def tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        fail(f"'{name}' not found on PATH. See docs/SETUP.md Phase 0.")
    return found


def run(cmd: list, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a command; on failure raise StudioError with the tail of its output."""
    proc = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd else None,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-25:])
        fail(f"command failed ({proc.returncode}): {' '.join(str(c) for c in cmd[:6])} …\n{tail}")
    return proc


def ffprobe_json(path: Path, count_frames: bool = False) -> dict:
    cmd = [tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams"]
    if count_frames:
        cmd += ["-count_packets"]
    cmd.append(path)
    return json.loads(run(cmd).stdout)


def media_duration(path: Path) -> float:
    return float(ffprobe_json(path)["format"]["duration"])


def video_info(path: Path) -> dict:
    """frames, fps, width, height, pix_fmt and stream counts of a media file."""
    info = ffprobe_json(path, count_frames=True)
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    out = {
        "video_streams": len(v),
        "audio_streams": len(a),
        "duration": float(info["format"].get("duration", 0)),
    }
    if v:
        num, den = v[0]["r_frame_rate"].split("/")
        out.update(
            frames=int(v[0].get("nb_read_packets", 0)),
            fps=float(num) / float(den),
            width=v[0]["width"],
            height=v[0]["height"],
            pix_fmt=v[0].get("pix_fmt"),
        )
    return out


def print_table(headers: list[str], rows: list[list]) -> None:
    cols = [headers] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in cols) for i in range(len(headers))]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for r in cols[1:]:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)))
