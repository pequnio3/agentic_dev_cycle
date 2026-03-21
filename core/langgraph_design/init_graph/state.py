from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict


class InitState(TypedDict, total=False):
    """Graph state for `/init-dev-cycle`. Optional keys omitted until set."""

    repo_root: Path

    init_agent_instructions: str
    """Bundled init prompt text from ``init_graph/prompt.md``."""

    init_agent_source: Path
    """Path to ``prompt.md`` (provenance)."""

    init_resume_raw: dict | str | None
    """Value passed when resuming from ``interrupt`` — JSON object or JSON string."""

    init_apply_errors: list[str]
    """Structured parse/write failures before on-disk validation."""

    init_validation_errors: list[str]

    last_interrupt: dict | str | None

    step: Literal[
        "init",
        "loaded_config",
        "await_init",
        "applied",
        "apply_failed",
        "validated",
        "done",
        "failed",
    ]
    errors: list[str]
