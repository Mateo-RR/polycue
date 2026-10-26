"""Move videos from the 0.1 layout (one video spread over several folders) to the 0.2 layout.

0.1:  manim_engine/scenes/<slug>/        →  0.2:  projects/<slug>/scenes/manim/
      remotion_engine/src/videos/<slug>/ →        projects/<slug>/scenes/remotion/
      output/<slug>/                     →        projects/<slug>/output/

Scene imports are rewritten on the way: `from scenes.<slug>.common import …` becomes
`from common import …` (render.py puts the scene folder on PYTHONPATH), and
`"../../studio/…"` becomes `"@studio/…"` (alias defined in remotion.config.ts and tsconfig.json).

Usage:
  migrate_layout.py [--slugs …] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from _studio import MANIM_ENGINE, REMOTION_ENGINE, REPO, fail, main_wrapper, print_table, rel

OLD_MANIM = MANIM_ENGINE / "scenes"
OLD_REMOTION = REMOTION_ENGINE / "src" / "videos"
OLD_OUTPUT = REPO / "output"
SKIP = {"__pycache__"}


def rewrite_manim(text: str, slug: str) -> str:
    return re.sub(rf"^(\s*(?:from|import)\s+)scenes\.{re.escape(slug)}\.", r"\1", text, flags=re.MULTILINE)


def rewrite_remotion(text: str) -> str:
    return re.sub(r"""(["'])(?:\.\./){2,}studio/""", r"\1@studio/", text)


def old_slugs() -> list[str]:
    found = set()
    for base in (OLD_MANIM, OLD_REMOTION, OLD_OUTPUT):
        if base.is_dir():
            found |= {p.name for p in base.iterdir() if p.is_dir() and p.name not in SKIP}
    return sorted(found)


def plan(slug: str) -> list[tuple[Path, Path]]:
    """(source folder, destination folder) pairs that exist for this slug."""
    project = REPO / "projects" / slug
    pairs = [(OLD_MANIM / slug, project / "scenes" / "manim"),
             (OLD_REMOTION / slug, project / "scenes" / "remotion"),
             (OLD_OUTPUT / slug, project / "output")]
    return [(src, dst) for src, dst in pairs if src.is_dir()]


def move_folder(src: Path, dst: Path, slug: str) -> int:
    """Move every file of src into dst (rewriting scene imports) and remove src. Returns the file count."""
    count = 0
    for path in sorted(src.rglob("*")):
        if not path.is_file() or SKIP & set(path.relative_to(src).parts):
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".py":
            target.write_text(rewrite_manim(path.read_text(encoding="utf-8"), slug), encoding="utf-8", newline="\n")
            path.unlink()
        elif path.suffix in (".ts", ".tsx"):
            target.write_text(rewrite_remotion(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
            path.unlink()
        else:
            shutil.move(str(path), target)
        count += 1
    shutil.rmtree(src)
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slugs", nargs="+", help="only these videos (default: every video in the old layout)")
    ap.add_argument("--dry-run", action="store_true", help="show what would move, change nothing")
    args = ap.parse_args()

    available = old_slugs()
    slugs = args.slugs or available
    unknown = [s for s in slugs if s not in available]
    if unknown:
        fail(f"not in the old layout: {unknown}; found {available}")
    if not slugs:
        print("Nothing to migrate: no videos in the old layout.")
        return

    jobs = {slug: plan(slug) for slug in slugs}
    clashes = [rel(dst) for pairs in jobs.values() for _, dst in pairs if dst.exists() and any(dst.iterdir())]
    if clashes:
        fail(f"destination folders already exist and are not empty, nothing was moved: {clashes}")

    rows = []
    for slug, pairs in jobs.items():
        for src, dst in pairs:
            files = sum(1 for p in src.rglob("*") if p.is_file() and not SKIP & set(p.relative_to(src).parts))
            if not args.dry_run:
                files = move_folder(src, dst, slug)
            rows.append([slug, rel(src), rel(dst), files])

    print_table(["video", "from", "to", "files"], rows)
    if args.dry_run:
        print("\nDry run: nothing was changed.")
        return

    ignore = REPO / ".gitignore"
    stale = [line for line in ignore.read_text(encoding="utf-8").splitlines()
             if line.startswith(("!manim_engine/scenes/", "!remotion_engine/src/videos/"))] if ignore.exists() else []
    if stale:
        print("\n.gitignore still whitelists old folders. Replace them with one `!projects/<slug>/` line per video:")
        for line in stale:
            print(f"  {line}")


if __name__ == "__main__":
    main_wrapper(main)
