"""Load bundled agent prompt markdown (design, build, review, …) from the repo."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from common.project_yaml import strip_html_comments


class Agent(str, Enum):
    """Agent id → directory under `.dev_cycle/agents/<id>/` (see `base.md` + `custom.md`)."""

    INIT = "init"
    DESIGN = "design"
    BUILD = "build"
    REVIEW = "review"
    FIX = "fix"
    DEPLOY = "deploy"


_LEGACY_FLAT: dict[Agent, str] = {
    Agent.INIT: "init_agent.md",
    Agent.DESIGN: "design_agent.md",
    Agent.BUILD: "build_agent.md",
    Agent.REVIEW: "review_agent.md",
    Agent.FIX: "fix_agent.md",
    Agent.DEPLOY: "deploy_agent.md",
}


def _merge_personality_base(base: str, custom_raw: str) -> str:
    """Insert ``## Personality`` after the first heading using cleaned ``custom.md`` content."""
    custom_clean = strip_html_comments(custom_raw).strip()
    if not custom_clean:
        custom_clean = (
            "*Optional personality — set in `custom.md` or via `/init-dev-cycle` "
            "(e.g. ML architecture vs UX emphasis).*"
        )
    base = base.strip()
    nl = base.find("\n")
    if nl == -1:
        return f"{base}\n\n## Personality\n\n{custom_clean}\n"
    title = base[:nl].rstrip()
    body = base[nl + 1 :].lstrip()
    return f"{title}\n\n## Personality\n\n{custom_clean}\n\n---\n\n{body}"


def _resolve_new_layout(repo: Path, kind: Agent) -> tuple[Path, Path] | None:
    for agents_root in (repo / ".dev_cycle" / "agents", repo / "core" / "agents"):
        d = agents_root / kind.value
        base = d / "base.md"
        if base.is_file():
            custom = d / "custom.md"
            return base, custom
    return None


def _resolve_legacy_flat(repo: Path, kind: Agent) -> Path | None:
    name = _LEGACY_FLAT[kind]
    for agents_root in (repo / ".dev_cycle" / "agents", repo / "core" / "agents"):
        p = agents_root / name
        if p.is_file():
            return p
    return None


def read_agent(repo: Path, kind: Agent) -> tuple[str, Path]:
    """
    Load the full agent prompt: ``base.md`` merged with ``custom.md`` (personality), or a legacy flat ``*_agent.md``.

    Prefer **installed** `.dev_cycle/agents/<name>/`; fall back to **`core/agents/`** in the workflow repo.
    Provenance path in the return value is **base.md** when using the new layout, else the legacy file.
    """
    resolved = _resolve_new_layout(repo, kind)
    if resolved:
        base_path, custom_path = resolved
        base = base_path.read_text(encoding="utf-8")
        custom = custom_path.read_text(encoding="utf-8") if custom_path.is_file() else ""
        merged = _merge_personality_base(base, custom)
        return merged, base_path.resolve()

    leg = _resolve_legacy_flat(repo, kind)
    if leg:
        return leg.read_text(encoding="utf-8"), leg.resolve()

    raise FileNotFoundError(
        f"agent {kind.name}: expected `.dev_cycle/agents/{kind.value}/base.md` "
        f"or legacy `{_LEGACY_FLAT[kind]}` under {repo}"
    )


def read_design_agent_markdown(repo: Path) -> tuple[str, Path]:
    """Same as ``read_agent(repo, Agent.DESIGN)`` — kept for call sites that only need design."""
    return read_agent(repo, Agent.DESIGN)
