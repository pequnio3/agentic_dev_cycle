"""Parse init resume JSON and write `.dev_cycle` artifacts (project.yaml, gates, custom.md)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_AGENTS: tuple[str, ...] = ("design", "build", "review", "fix", "deploy")


def parse_init_submit(raw: object) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Validate resume payload shape.

    Expected top-level keys:
    - **project** — mapping serialized to `.dev_cycle/project.yaml`
    - **gates_config_sh** — full contents of `.dev_cycle/gates_config.sh`
    - **agents** — mapping of agent name → `custom.md` body (required: design, build, review, fix, deploy)
    """
    errs: list[str] = []
    if raw is None:
        return None, ["resume payload is missing — pass a JSON object when resuming"]

    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, [f"resume JSON parse error: {e}"]

    if not isinstance(data, dict):
        return None, ["resume payload must be a JSON object (or a JSON string of an object)"]

    proj = data.get("project")
    if not isinstance(proj, dict):
        errs.append('top-level "project" must be a mapping (YAML root content)')

    gcs = data.get("gates_config_sh")
    if not isinstance(gcs, str):
        errs.append('top-level "gates_config_sh" must be a string (full gates_config.sh body)')
    elif not gcs.strip():
        errs.append('top-level "gates_config_sh" must be non-empty')

    agents = data.get("agents")
    if not isinstance(agents, dict):
        errs.append('top-level "agents" must be a mapping of agent name → custom.md text')
    else:
        for name in REQUIRED_AGENTS:
            v = agents.get(name)
            if not isinstance(v, str):
                errs.append(f'agents["{name}"] must be a string (custom.md body)')
            elif not v.strip():
                errs.append(f'agents["{name}"] is empty — add at least a short personality block')

    if errs:
        return None, errs
    return data, []


def apply_init_submit(repo: Path, data: dict[str, Any]) -> list[str]:
    """Write files under ``repo/.dev_cycle/``. Returns error strings; empty on success."""
    dc = repo / ".dev_cycle"
    dc.mkdir(parents=True, exist_ok=True)
    (dc / "agents").mkdir(parents=True, exist_ok=True)

    errs: list[str] = []
    proj = data["project"]
    try:
        yaml_text = yaml.safe_dump(
            proj,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        (dc / "project.yaml").write_text(yaml_text, encoding="utf-8")
    except OSError as e:
        errs.append(f"failed to write project.yaml: {e}")
        return errs
    except yaml.YAMLError as e:
        return [f"project mapping is not YAML-serializable: {e}"]

    gcs = data["gates_config_sh"]
    try:
        body = gcs if gcs.lstrip().startswith("#!") else f"#!/bin/bash\n{gcs}"
        (dc / "gates_config.sh").write_text(body, encoding="utf-8")
    except OSError as e:
        errs.append(f"failed to write gates_config.sh: {e}")
        return errs

    agents = data["agents"]
    for name in REQUIRED_AGENTS:
        path = dc / "agents" / name / "custom.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(agents[name], encoding="utf-8")
        except OSError as e:
            errs.append(f"failed to write {path}: {e}")

    opt = agents.get("init")
    if isinstance(opt, str) and opt.strip():
        p = dc / "agents" / "init" / "custom.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.write_text(opt, encoding="utf-8")
        except OSError as e:
            errs.append(f"failed to write {p}: {e}")

    return errs
