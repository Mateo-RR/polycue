"""Check that everything the studio needs is installed, and say how to fix what is missing.

Reports only: it never installs anything. Unlike the other scripts, it runs with any Python 3
(the system one before the venv exists, or the venv one afterwards) and uses only the stdlib.

Usage:
  doctor.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from _studio import MANIM_ENGINE, REMOTION_ENGINE, SHARED, main_wrapper, print_table

MIN_PYTHON = (3, 12)
MIN_NODE = 18

if sys.platform == "win32":
    OS = "windows"
elif sys.platform == "darwin":
    OS = "macos"
else:
    OS = "linux"

VENV_PY = MANIM_ENGINE / ".venv" / ("Scripts/python.exe" if OS == "windows" else "bin/python")
VENV_PY_SHOWN = r"manim_engine\.venv\Scripts\python" if OS == "windows" else "manim_engine/.venv/bin/python"

# How to fix each check, per OS. "any" applies when there is no OS-specific entry.
FIXES = {
    "python": {
        "windows": "winget install Python.Python.3.13",
        "macos": "brew install python@3.13",
        "linux": "sudo apt install python3.12 python3.12-venv  (or your distro's equivalent)",
    },
    "node": {
        "windows": "winget install OpenJS.NodeJS.LTS",
        "macos": "brew install node",
        "linux": "install Node LTS from https://nodejs.org or with nvm",
    },
    "ffmpeg": {
        "windows": "winget install Gyan.FFmpeg",
        "macos": "brew install ffmpeg",
        "linux": "sudo apt install ffmpeg",
    },
    "libass": {"any": "install an ffmpeg build with libass (the builds suggested above include it)"},
    "latex": {
        "windows": "winget install MiKTeX.MiKTeX",
        "macos": "brew install --cask mactex-no-gui",
        "linux": "sudo apt install texlive texlive-latex-extra dvisvgm",
    },
    "cairo": {"linux": "sudo apt install libcairo2-dev libpango1.0-dev pkg-config"},
    "fonts": {"any": "install the TTF files in shared/fonts/ for your user (docs/SETUP.md, Phase 1)"},
    "venv": {"any": f"python -m venv manim_engine/.venv && {VENV_PY_SHOWN} -m pip install -r manim_engine/requirements.txt"},
    "packages": {"any": f"{VENV_PY_SHOWN} -m pip install -r manim_engine/requirements.txt"},
    "node_modules": {"any": "cd remotion_engine && npm ci"},
}


def output_of(cmd: list[str]) -> str | None:
    """stdout+stderr of a command, or None if it cannot run or fails."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        proc = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout + proc.stderr if proc.returncode == 0 else None


def first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else ""


def check_python() -> tuple[bool, str]:
    found = ".".join(map(str, sys.version_info[:3]))
    return sys.version_info[:2] >= MIN_PYTHON, f"{found} (needs >= {'.'.join(map(str, MIN_PYTHON))})"


def check_node() -> tuple[bool, str]:
    out = output_of(["node", "--version"])
    if out is None:
        return False, "not found"
    match = re.search(r"v(\d+)", out)
    major = int(match.group(1)) if match else 0
    return major >= MIN_NODE and shutil.which("npm") is not None, \
        f"{out.strip()} (needs >= {MIN_NODE}, with npm)"


def check_tools(*names: str) -> tuple[bool, str]:
    outputs = {n: output_of([n, "-version" if n.startswith("ff") else "--version"]) for n in names}
    missing = [n for n, out in outputs.items() if out is None]
    if missing:
        return False, "not found: " + ", ".join(missing)
    return True, first_line(outputs[names[0]])[:60]


def check_libass() -> tuple[bool, str]:
    out = output_of(["ffmpeg", "-hide_banner", "-filters"])
    if out is None:
        return False, "ffmpeg not found"
    ok = any(re.match(r"^\s*\S+\s+ass\s", line) for line in out.splitlines())
    return ok, "ass filter available" if ok else "this ffmpeg build has no 'ass' filter"


def check_cairo() -> tuple[bool, str]:
    ok = output_of(["pkg-config", "--exists", "cairo", "pangocairo"]) is not None
    return ok, "cairo + pangocairo found" if ok else "pkg-config cannot find cairo / pangocairo"


def font_dirs() -> list[Path]:
    home = Path.home()
    if OS == "windows":
        return [Path(os.environ.get("LOCALAPPDATA", home)) / "Microsoft/Windows/Fonts",
                Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"]
    if OS == "macos":
        return [home / "Library/Fonts", Path("/Library/Fonts")]
    return [home / ".local/share/fonts", home / ".fonts", Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]


def check_fonts() -> tuple[bool, str]:
    families = sorted({p.stem.split("-")[0] for p in SHARED.glob("fonts/*.ttf")})
    installed = " ".join(p.name.lower().replace(" ", "")
                         for d in font_dirs() if d.is_dir() for p in d.rglob("*") if p.suffix.lower() in (".ttf", ".otf"))
    missing = [f for f in families if f.lower() not in installed]
    return not missing, "not installed: " + ", ".join(missing) if missing else ", ".join(families)


def check_venv() -> tuple[bool, str]:
    if not VENV_PY.exists():
        return False, "manim_engine/.venv not found"
    out = output_of([str(VENV_PY), "--version"])
    return out is not None, first_line(out or "venv python does not run")


def check_packages() -> tuple[bool, str]:
    """Every `name==version` pin in requirements.txt is installed in the venv with that version."""
    if not VENV_PY.exists():
        return False, "no venv"
    pins = {}
    for line in (MANIM_ENGINE / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if "==" in line and ";" not in line:  # lines with environment markers are skipped
            name, version = line.strip().split("==")
            pins[name] = version
    probe = (
        "import json, sys, importlib.metadata as m\n"
        "out = {}\n"
        "for name in json.loads(sys.argv[1]):\n"
        "    try: out[name] = m.version(name)\n"
        "    except m.PackageNotFoundError: out[name] = None\n"
        "print(json.dumps(out))\n"
    )
    out = output_of([str(VENV_PY), "-c", probe, json.dumps(list(pins))])
    if out is None:
        return False, "could not query the venv"
    installed = json.loads(out)
    wrong = [f"{n} {installed[n] or 'missing'} (pinned {v})" for n, v in pins.items() if installed[n] != v]
    if wrong:
        return False, f"{len(wrong)} mismatched: " + ", ".join(wrong[:3]) + (" …" if len(wrong) > 3 else "")
    return True, f"{len(pins)} pinned packages match"


def check_node_modules() -> tuple[bool, str]:
    pinned = json.loads((REMOTION_ENGINE / "package.json").read_text(encoding="utf-8"))["dependencies"]["remotion"]
    installed_pkg = REMOTION_ENGINE / "node_modules/remotion/package.json"
    if not installed_pkg.exists():
        return False, "remotion_engine/node_modules not found"
    installed = json.loads(installed_pkg.read_text(encoding="utf-8"))["version"]
    return installed == pinned, f"remotion {installed} (pinned {pinned})"


def main() -> None:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()

    checks = [
        ("Python", "python", check_python),
        ("Node.js + npm", "node", check_node),
        ("ffmpeg + ffprobe", "ffmpeg", lambda: check_tools("ffmpeg", "ffprobe")),
        ("ffmpeg libass", "libass", check_libass),
        ("LaTeX + dvisvgm", "latex", lambda: check_tools("latex", "dvisvgm")),
    ]
    if OS == "linux":
        checks.append(("Cairo + Pango", "cairo", check_cairo))
    checks += [
        ("Fonts (system)", "fonts", check_fonts),
        ("Python venv", "venv", check_venv),
        ("Python packages", "packages", check_packages),
        ("Remotion packages", "node_modules", check_node_modules),
    ]

    rows, failed = [], []
    for label, key, fn in checks:
        ok, detail = fn()
        rows.append([label, "ok" if ok else "MISSING", detail])
        if not ok:
            failed.append((label, key))

    print(f"Studio doctor ({OS})\n")
    print_table(["Check", "Status", "Detail"], rows)

    if not failed:
        print("\nEverything is installed.")
        return
    print("\nHow to fix:")
    for label, key in failed:
        fix = FIXES[key].get(OS) or FIXES[key].get("any")
        print(f"  - {label}: {fix}")
    print("\nSystem installs (winget, brew, apt) may need admin rights. See docs/SETUP.md for details.")
    sys.exit(1)


if __name__ == "__main__":
    main_wrapper(main)
