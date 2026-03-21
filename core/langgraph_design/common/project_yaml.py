"""Load `.dev_cycle/project.yaml` — structured project config (replaces project.md + models.json)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from common.project import parse_design_model_from_project

REQUIRED_MODEL_AGENTS: tuple[str, ...] = ("design", "build", "review", "fix", "deploy")

PROJECT_YAML_REL = Path(".dev_cycle") / "project.yaml"


def strip_html_comments(s: str) -> str:
    """Remove `<!-- ... -->` blocks (non-greedy)."""
    return re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)


def load_project_yaml(repo: Path) -> dict[str, Any] | None:
    """Load merged project config from ``.dev_cycle/project.yaml`` or ``core/project.yaml``."""
    for rel in (PROJECT_YAML_REL, Path("core") / "project.yaml"):
        p = repo / rel
        if not p.is_file():
            continue
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return data
    return None


def _model_id_for_agent(models: Any, agent: str) -> str | None:
    if not isinstance(models, dict):
        return None
    entry = models.get(agent)
    if isinstance(entry, dict):
        m = entry.get("model")
        if isinstance(m, str) and m.strip():
            return m.strip()
    elif isinstance(entry, str) and entry.strip():
        return entry.strip()
    return None


def parse_design_model(repo: Path) -> str:
    """
    Resolve the model id for the design agent.

    Order: **project.yaml** ``models.design`` → legacy **models.json** → **project.md** Models table.
    """
    data = load_project_yaml(repo)
    if data:
        mid = _model_id_for_agent(data.get("models"), "design")
        if mid:
            return mid

    # Legacy: flat models.json
    for rel in (Path(".dev_cycle") / "models.json", Path("core") / "models.json"):
        p = repo / rel
        if not p.is_file():
            continue
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(m, dict) and isinstance(m.get("design"), str) and m["design"].strip():
            return m["design"].strip()

    # Legacy: project.md table
    for rel in (Path(".dev_cycle") / "project.md", Path("core") / "project.md"):
        p = repo / rel
        if p.is_file():
            return parse_design_model_from_project(p.read_text(encoding="utf-8"))

    return "claude-opus-4-6"


def validate_project_yaml(repo: Path) -> list[str]:
    """Validate ``.dev_cycle/project.yaml`` for init graph completion."""
    errs: list[str] = []
    p = repo / ".dev_cycle" / "project.yaml"
    if not p.is_file():
        errs.append(f"Missing {p}")
        return errs
    try:
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return [f"project.yaml parse error: {e}"]
    if not isinstance(data, dict):
        return ["project.yaml must be a mapping at the root"]

    models = data.get("models")
    for agent in REQUIRED_MODEL_AGENTS:
        mid = _model_id_for_agent(models, agent)
        if not mid:
            errs.append(f"project.yaml: models.{agent}.model must be a non-empty string")

    proj = data.get("project")
    if isinstance(proj, dict):
        name = str(proj.get("name", "")).strip()
        desc = str(proj.get("description", "")).strip()
        stack = str(proj.get("stack", "")).strip()
        if not (name or desc or stack):
            errs.append(
                "project.yaml: set at least one of project.name, project.description, or project.stack"
            )
    else:
        errs.append("project.yaml: missing `project` mapping")

    tsd = str(data.get("tech_stack_details") or "")
    if len(strip_html_comments(tsd).strip()) < 80:
        errs.append("project.yaml: tech_stack_details is too short after removing comment placeholders")

    return errs


def render_project_context_markdown(repo: Path) -> str:
    """
    Render ``project.yaml`` as a markdown block for injecting into agent prompts downstream.

    Returns empty string if no YAML is present.
    """
    data = load_project_yaml(repo)
    if not data:
        return ""

    lines: list[str] = ["## Project context (`project.yaml`)", ""]

    proj = data.get("project")
    if isinstance(proj, dict):
        if proj.get("name"):
            lines.append(f"- **Name:** {proj['name']}")
        if proj.get("description"):
            lines.append(f"- **Description:** {proj['description']}")
        if proj.get("stack"):
            lines.append(f"- **Stack:** {proj['stack']}")
        if proj.get("repo"):
            lines.append(f"- **Repo:** {proj['repo']}")
        lines.append("")

    for key, title in (
        ("tech_stack_details", "### Tech stack details"),
        ("architecture_patterns", "### Architecture patterns"),
    ):
        block = str(data.get(key) or "").strip()
        if block:
            lines.append(title)
            lines.append(block)
            lines.append("")

    imp = str(data.get("implementation_phases") or "").strip()
    if imp:
        lines.append("### Implementation phases")
        lines.append(imp)
        lines.append("")

    gc = data.get("gate_commands")
    if isinstance(gc, dict):
        lines.append("### Gate commands (human summary)")
        for k, label in (
            ("iteration", "Iteration (`gates.sh iteration`)"),
            ("pre_pr", "Pre-PR"),
            ("final", "Final"),
        ):
            text = gc.get(k)
            if text:
                lines.append(f"- **{label}:** {text}")
        lines.append("")

    models = data.get("models")
    if isinstance(models, dict):
        lines.append("### Models (per agent)")
        for agent in REQUIRED_MODEL_AGENTS:
            mid = _model_id_for_agent(models, agent)
            if mid:
                reason = ""
                ent = models.get(agent)
                if isinstance(ent, dict) and ent.get("reason"):
                    reason = f" — {ent['reason']}"
                lines.append(f"- **{agent}:** `{mid}`{reason}")
        lines.append("")

    bn = data.get("branch_naming")
    if isinstance(bn, dict):
        lines.append(f"### Branch naming: prefix `{bn.get('prefix', 'dev-')}`")

    notes = str(data.get("code_style_notes") or "").strip()
    if notes:
        lines.append("### Code style notes")
        lines.append(notes)

    return "\n".join(lines).strip()
