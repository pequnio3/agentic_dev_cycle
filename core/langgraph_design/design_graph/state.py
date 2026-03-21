from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict

from common.types import PhaseSpec

__all__ = ["DesignState", "PhaseSpec"]


class DesignState(TypedDict, total=False):
    """Graph state for `/design`. Optional keys are omitted until set."""

    # --- inputs ---
    repo_root: Path
    """Repository root (contains `.dev_cycle/`)."""

    raw_input: str
    """File path to `.dev_cycle/design/<slug>.md` or a free-text phrase (slug derived)."""

    # --- resolved ---
    slug: str
    design_path: Path
    design_model: str
    """Model id from `.dev_cycle/project.yaml` ``models.design`` (or legacy fallbacks)."""

    design_agent_instructions: str
    """Merged design prompt (`agents/design/base.md` + `custom.md`) — embedded for sub-agents."""

    design_agent_source: Path
    """Path to `base.md` used as provenance for the merged prompt."""

    # --- validation ---
    design_body: str
    design_validation_errors: list[str]

    # --- human checkpoints (resume payloads) ---
    last_interrupt: dict | str | None

    # --- git / GitHub ---
    merge_ran: bool
    labels_ok: bool
    next_work_order_index: int
    phases: list[PhaseSpec]
    created_issue_urls: list[str]

    # --- terminal ---
    step: Literal[
        "init",
        "resolved",
        "loaded_config",
        "await_design",
        "validated",
        "await_approval",
        "merged",
        "labeled",
        "issues_created",
        "done",
        "failed",
    ]
    errors: list[str]
