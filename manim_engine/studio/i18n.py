"""Visible text for Manim scenes, loaded from projects/<slug>/locales/<lang>/strings.json."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Render scenes through scripts/render.py.")
    return value


def strings_path() -> Path:
    return REPO_ROOT / "projects" / _env("STUDIO_SLUG") / "locales" / _env("STUDIO_LANG") / "strings.json"


@lru_cache(maxsize=None)
def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"strings file not found: {p}")
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def S(key: str) -> str:
    """Return the localized string for ``key``."""
    path = strings_path()
    data = _load(str(path))
    if key not in data:
        raise KeyError(f"Missing string key {key!r} in {path.relative_to(REPO_ROOT)}")
    return data[key]
