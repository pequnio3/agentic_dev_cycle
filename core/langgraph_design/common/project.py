"""Legacy: parse the Models **table** from old ``project.md`` (used if YAML/JSON absent)."""

from __future__ import annotations

import re


def parse_design_model_from_project(project_md: str) -> str:
    """Return model id for the `design` row in the Models table, or default."""
    default = "claude-opus-4-6"
    for line in project_md.splitlines():
        line_stripped = line.strip()
        if not line_stripped.startswith("|"):
            continue
        parts = [p.strip() for p in line_stripped.split("|")]
        parts = [p for p in parts if p]
        if len(parts) >= 2 and parts[0].lower() == "design":
            cell = parts[1]
            cell = re.sub(r"<!--.*?-->", "", cell).strip()
            if cell and not cell.lower().startswith("e.g."):
                return cell
            m = re.search(r"`([^`]+)`", line)
            if m:
                return m.group(1).strip()
    return default
