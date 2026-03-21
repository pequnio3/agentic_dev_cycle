"""Subprocess helpers for gh, git, and other CLI tools."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_cmd(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a subprocess; return (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""
