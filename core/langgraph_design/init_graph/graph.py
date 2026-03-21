"""
Init workflow: interview the user (via external agent), collect structured JSON,
then apply `project.yaml`, `gates_config.sh`, and `agents/<name>/custom.md`.

Mirrors [`../skills/init-dev-cycle/SKILL.md`](../../skills/init-dev-cycle/SKILL.md).
"""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from common.agent import Agent
from common.project_yaml import validate_project_yaml
from init_graph.apply import apply_init_submit, parse_init_submit
from init_graph.prompt import load_init_prompt
from init_graph.state import InitState

# Agent files that must exist and be non-trivial after init (excludes INIT prompt itself).
_WORKFLOW_AGENT_FILES: tuple[Agent, ...] = (
    Agent.DESIGN,
    Agent.BUILD,
    Agent.REVIEW,
    Agent.FIX,
    Agent.DEPLOY,
)


def _err(state: InitState, msg: str) -> dict:
    errs = list(state.get("errors", []))
    errs.append(msg)
    return {"errors": errs, "step": "failed"}


def node_prepare(state: InitState) -> dict:
    repo = Path(state["repo_root"]).resolve()
    if not repo.is_dir():
        return _err(state, f"repo_root is not a directory: {repo}")

    dc = repo / ".dev_cycle"
    dc.mkdir(parents=True, exist_ok=True)
    (dc / "agents").mkdir(parents=True, exist_ok=True)

    try:
        agent_md = load_init_prompt()
    except OSError as e:
        return _err(state, f"failed to load bundled init prompt: {e}")

    prompt_path = Path(__file__).resolve().parent / "prompt.md"
    return {
        "init_agent_instructions": agent_md,
        "init_agent_source": prompt_path,
        "step": "loaded_config",
        "errors": [],
    }


def node_await_init(state: InitState) -> dict:
    repo = Path(state["repo_root"])
    agent_text = state.get("init_agent_instructions")
    if not agent_text:
        try:
            agent_text = load_init_prompt()
        except OSError as e:
            return _err(state, f"failed to load bundled init prompt: {e}")

    project_yaml = repo / ".dev_cycle" / "project.yaml"
    gates = repo / ".dev_cycle" / "gates_config.sh"
    agents_dir = repo / ".dev_cycle" / "agents"

    resume_payload = interrupt(
        {
            "checkpoint": "await_init",
            "instructions": (
                "Run the init agent: follow **agent_instructions** (bundled `init_graph/prompt.md`). "
                "The agent is read-only (no file edits, no mutating shell commands). When the JSON "
                "is ready, **resume** with one object: keys `project`, `gates_config_sh`, `agents` "
                "(see prompt). This workflow writes `.dev_cycle/` from that payload and validates."
            ),
            "agent_instructions": agent_text,
            "agent_instructions_source": str(state.get("init_agent_source") or ""),
            "project_yaml": str(project_yaml),
            "gates_config_sh": str(gates),
            "agents_dir": str(agents_dir),
            "repo_root": str(repo),
        }
    )
    return {
        "last_interrupt": resume_payload,
        "init_resume_raw": resume_payload,
        "step": "await_init",
    }


def node_apply_init(state: InitState) -> dict:
    repo = Path(state["repo_root"]).resolve()
    raw = state.get("init_resume_raw")
    data, parse_errs = parse_init_submit(raw)
    if parse_errs:
        return {
            "init_apply_errors": parse_errs,
            "init_validation_errors": parse_errs,
            "step": "apply_failed",
        }
    assert data is not None
    write_errs = apply_init_submit(repo, data)
    if write_errs:
        return {
            "init_apply_errors": write_errs,
            "init_validation_errors": write_errs,
            "step": "apply_failed",
        }
    return {"init_apply_errors": [], "step": "applied"}


def _validate_init_files(repo: Path) -> list[str]:
    errs: list[str] = []
    errs.extend(validate_project_yaml(repo))

    gates = repo / ".dev_cycle" / "gates_config.sh"
    if not gates.is_file():
        errs.append(f"Missing {gates}")
    else:
        gtxt = gates.read_text(encoding="utf-8", errors="replace")
        if "run_iteration_gate" not in gtxt:
            errs.append("gates_config.sh must define run_iteration_gate() (sourced by gates.sh).")
        if "run_pre_pr_gate" not in gtxt:
            errs.append("gates_config.sh must define run_pre_pr_gate().")

    agents_dir = repo / ".dev_cycle" / "agents"
    if not agents_dir.is_dir():
        errs.append(f"Missing directory {agents_dir}")
    else:
        for kind in _WORKFLOW_AGENT_FILES:
            d = agents_dir / kind.value
            base = d / "base.md"
            custom = d / "custom.md"
            if not d.is_dir():
                errs.append(f"Missing agent directory {d} (expected base.md + custom.md)")
                continue
            if not base.is_file():
                errs.append(f"Missing {base}")
            elif base.stat().st_size < 80:
                errs.append(f"base.md too small for agent {kind.value!r}")
            if not custom.is_file():
                errs.append(f"Missing {custom} (may be comment-only)")

        init_d = agents_dir / Agent.INIT.value
        if not init_d.is_dir() or not (init_d / "base.md").is_file():
            errs.append(f"Expected init agent at {init_d}/base.md")

    return errs


def node_validate_init(state: InitState) -> dict:
    repo = Path(state["repo_root"])
    errs = _validate_init_files(repo)
    if errs:
        return {"init_validation_errors": errs, "step": "validated"}
    return {"init_validation_errors": [], "step": "validated"}


def route_after_validate(state: InitState) -> str:
    if state.get("errors"):
        return "end"
    ve = state.get("init_validation_errors") or []
    if ve:
        return "await_init_retry"
    return "done"


def route_after_prepare(state: InitState) -> str:
    if state.get("step") == "failed" or state.get("errors"):
        return "end"
    return "await_init"


def route_after_await_init(state: InitState) -> str:
    """Skip apply if the node failed before ``interrupt`` (e.g. missing bundled prompt)."""
    if state.get("step") == "failed" or state.get("errors"):
        return "end"
    return "apply_init"


def route_after_await_init_retry(state: InitState) -> str:
    if state.get("step") == "failed" or state.get("errors"):
        return "end"
    return "apply_init"


def route_after_apply(state: InitState) -> str:
    if state.get("step") == "failed" or state.get("errors"):
        return "end"
    ae = state.get("init_apply_errors") or []
    if ae:
        return "await_init_retry"
    return "validate_init"


def node_await_init_retry(state: InitState) -> dict:
    repo = Path(state["repo_root"])
    agent_text = state.get("init_agent_instructions")
    if not agent_text:
        try:
            agent_text = load_init_prompt()
        except OSError as e:
            return _err(state, f"failed to load bundled init prompt: {e}")

    resume_payload = interrupt(
        {
            "checkpoint": "await_init_fix",
            "instructions": (
                "Fix the init configuration. Address **validation_errors**. **agent_instructions** "
                "is the full spec (read-only agent). **Resume** with an updated JSON object "
                "(`project`, `gates_config_sh`, `agents`) — same schema as before."
            ),
            "agent_instructions": agent_text,
            "validation_errors": state.get("init_validation_errors", []),
            "project_yaml": str(repo / ".dev_cycle" / "project.yaml"),
            "gates_config_sh": str(repo / ".dev_cycle" / "gates_config.sh"),
            "agents_dir": str(repo / ".dev_cycle" / "agents"),
        }
    )
    return {
        "last_interrupt": resume_payload,
        "init_resume_raw": resume_payload,
        "step": "await_init",
    }


def node_done(state: InitState) -> dict:
    return {
        "step": "done",
        "message": (
            "Init config passed validation. Commit and push when ready:\n"
            "  git add .dev_cycle/project.yaml .dev_cycle/gates_config.sh .dev_cycle/agents/\n"
            '  git commit -m "dev_cycle: init config"\n'
            "  git push origin main"
        ),
    }


def build_init_graph():
    """
    Compile the `/init-dev-cycle` LangGraph.

    Checkpoints (interrupt):
    - **await_init** — run init agent; resume with JSON → apply → validate
    - **await_init_fix** — fix validation errors; resume with JSON → apply → validate
    """
    g = StateGraph(InitState)
    g.add_node("prepare", node_prepare)
    g.add_node("await_init", node_await_init)
    g.add_node("apply_init", node_apply_init)
    g.add_node("validate_init", node_validate_init)
    g.add_node("await_init_retry", node_await_init_retry)
    g.add_node("done", node_done)

    g.add_edge(START, "prepare")
    g.add_conditional_edges(
        "prepare",
        route_after_prepare,
        {"await_init": "await_init", "end": END},
    )
    g.add_conditional_edges(
        "await_init",
        route_after_await_init,
        {"apply_init": "apply_init", "end": END},
    )
    g.add_conditional_edges(
        "apply_init",
        route_after_apply,
        {"validate_init": "validate_init", "await_init_retry": "await_init_retry", "end": END},
    )
    g.add_conditional_edges(
        "validate_init",
        route_after_validate,
        {"await_init_retry": "await_init_retry", "done": "done", "end": END},
    )
    g.add_conditional_edges(
        "await_init_retry",
        route_after_await_init_retry,
        {"apply_init": "apply_init", "end": END},
    )
    g.add_edge("done", END)

    return g.compile(checkpointer=MemorySaver())
