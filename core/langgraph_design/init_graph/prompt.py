"""Load the bundled init prompt (`prompt.md`) shipped with the init graph package."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def load_init_prompt() -> str:
    """Return the full init-agent instruction text (same for every run)."""
    try:
        return resources.files("init_graph").joinpath("prompt.md").read_text(encoding="utf-8")
    except (OSError, FileNotFoundError, TypeError, ValueError):
        here = Path(__file__).resolve().parent / "prompt.md"
        return here.read_text(encoding="utf-8")
