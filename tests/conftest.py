import sys
from pathlib import Path

# The studio scripts import each other as top-level modules (e.g. `from _studio import …`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# Pure-Python helpers of the Manim engine (e.g. studio.zoom_path) are tested without Manim.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "manim_engine"))
