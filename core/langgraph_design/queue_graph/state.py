from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from common.types import PhaseSpec


class QueueState(TypedDict, total=False):
    """State for the queue subgraph (labels → phases → GitHub issues)."""

    repo_root: Path
    slug: str
    design_body: str

    labels_ok: bool
    phases: list[PhaseSpec]
    next_work_order_index: int
    created_issue_urls: list[str]

    step: str
    errors: list[str]
