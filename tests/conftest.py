import sys
from pathlib import Path

# The studio scripts import each other as top-level modules (e.g. `from _studio import …`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
