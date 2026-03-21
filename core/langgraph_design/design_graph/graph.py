from __future__ import annotations

import os
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from common.agent import Agent, read_agent
from common.project_yaml import parse_design_model
from common.shell import run_cmd
from common.strings import kebab_case
from design_graph.state import DesignState
from queue_graph import build_queue_graph


def _err(state: DesignState, msg: str) -> dict:
    errs = list(state.get("errors", []))
    errs.append(msg)
    return {"errors": errs, "step": "failed"}


def node_resolve_and_load(state: DesignState) -> dict:
    repo = Path(state["repo_root"]).resolve()
    raw = state["raw_input"].strip()
    if not raw:
        return _err(state, "raw_input is empty")

    p = Path(raw)
    if p.suffix.lower() == ".md" or "/design/" in raw or "\\design\\" in raw:
        path = (repo / raw).resolve() if not p.is_absolute() else p.resolve()
        if not str(path).startswith(str(repo)):
            return _err(state, "Design path must be inside repo_root")
        slug = path.stem
    else:
        slug = kebab_case(raw)
        path = repo / ".dev_cycle" / "design" / f"{slug}.md"

    project_yaml = repo / ".dev_cycle" / "project.yaml"
    if not project_yaml.is_file():
        core_py = repo / "core" / "project.yaml"
        if not core_py.is_file():
            return _err(
                state,
                f"Missing {repo / '.dev_cycle' / 'project.yaml'} (install) or {core_py} — "
                "run install.sh on this repo and/or /init-dev-cycle",
            )

    model = parse_design_model(repo)

    try:
        agent_md, agent_src = read_agent(repo, Agent.DESIGN)
    except FileNotFoundError as e:
        return _err(state, str(e))

    return {
        "slug": slug,
        "design_path": path,
        "design_model": model,
        "design_agent_instructions": agent_md,
        "design_agent_source": agent_src,
        "step": "loaded_config",
        "errors": [],
    }


def node_await_design(state: DesignState) -> dict:
    """Human / external agent: draft design using embedded `design_agent` text; then resume."""
    path = state["design_path"]
    agent_text = state.get("design_agent_instructions")
    agent_src = state.get("design_agent_source")
    if not agent_text:
        try:
            agent_text, agent_src = read_agent(Path(state["repo_root"]), Agent.DESIGN)
        except FileNotFoundError as e:
            return _err(state, str(e))

    resume_payload = interrupt(
        {
            "checkpoint": "await_design",
            "instructions": (
                "Run as the design agent: follow **agent_instructions** below exactly (full text loaded from disk by the graph). "
                "Write the design doc to **design_file**. Do not merge to main yet."
            ),
            "agent_instructions": agent_text,
            "agent_instructions_source": str(agent_src) if agent_src else None,
            "design_file": str(path),
            "slug": state["slug"],
            "model": state["design_model"],
        }
    )
    return {
        "step": "await_design",
        "last_interrupt": resume_payload,
    }


def node_validate_design(state: DesignState) -> dict:
    path: Path = state["design_path"]
    if not path.is_file():
        return {
            **_err(state, f"Design file not found: {path}"),
            "design_validation_errors": [f"missing file: {path}"],
        }

    body = path.read_text(encoding="utf-8", errors="replace")
    errs: list[str] = []
    if len(body.strip()) < 80:
        errs.append("Design file is too short to be a complete design.")
    lower = body.lower()
    if "the problem" not in lower and "problem" not in lower[:200]:
        errs.append("Expected a Problem section (or similar) in the design doc.")
    if "context manifest" not in lower:
        errs.append("Expected a Context Manifest section per dev-cycle conventions.")

    if errs:
        return {"design_body": body, "design_validation_errors": errs, "step": "validated"}

    return {"design_body": body, "design_validation_errors": [], "step": "validated"}


def route_after_validate(state: DesignState) -> str:
    errs = state.get("design_validation_errors") or []
    if errs:
        return "await_design_retry"
    return "await_approval"


def route_after_resolve(state: DesignState) -> str:
    if state.get("step") == "failed" or state.get("errors"):
        return "end"
    return "await_design"


def route_after_merge(state: DesignState) -> str:
    if state.get("errors"):
        return "end"
    return "run_queue"


def route_after_queue(state: DesignState) -> str:
    if state.get("errors"):
        return "end"
    return "done"


def node_run_queue(state: DesignState) -> dict:
    """Run the queue subgraph (labels → phases → GitHub issues) and merge results into design state."""
    q = build_queue_graph()
    qout = q.invoke(
        {
            "repo_root": state["repo_root"],
            "slug": state["slug"],
            "design_body": state.get("design_body") or "",
        },
    )
    prior = list(state.get("errors", []))
    if qout.get("errors"):
        prior.extend(qout["errors"])
        return {
            "errors": prior,
            "phases": qout.get("phases"),
            "next_work_order_index": qout.get("next_work_order_index"),
            "created_issue_urls": qout.get("created_issue_urls", []),
            "step": "failed",
        }
    return {
        "phases": qout.get("phases"),
        "next_work_order_index": qout.get("next_work_order_index"),
        "created_issue_urls": qout.get("created_issue_urls", []),
        "labels_ok": qout.get("labels_ok"),
        "step": "done",
    }


def node_await_design_retry(state: DesignState) -> dict:
    """Tell human to fix validation; same checkpoint as draft, with errors attached."""
    agent_text = state.get("design_agent_instructions")
    if not agent_text:
        try:
            agent_text, _ = read_agent(Path(state["repo_root"]), Agent.DESIGN)
        except FileNotFoundError as e:
            return _err(state, str(e))
    interrupt(
        {
            "checkpoint": "await_design_fix",
            "instructions": (
                "Fix the design file so validation passes. **agent_instructions** is the same design-agent spec; "
                "update **design_file** accordingly."
            ),
            "agent_instructions": agent_text,
            "validation_errors": state.get("design_validation_errors", []),
            "design_file": str(state["design_path"]),
        }
    )
    return {"step": "await_design"}


def node_await_approval(state: DesignState) -> dict:
    interrupt(
        {
            "checkpoint": "await_approval",
            "message": (
                "Confirm the design agent has run **close out** (commit + push to `design/<slug>`). "
                "Then resume this graph to merge the design file into `main` and create GitHub issues."
            ),
            "slug": state["slug"],
        }
    )
    return {"step": "await_approval"}


def node_merge_to_main(state: DesignState) -> dict:
    repo = Path(state["repo_root"])
    slug = state["slug"]
    rel = Path(".dev_cycle/design") / f"{slug}.md"
    cmds = [
        ["git", "fetch", "origin"],
        ["git", "checkout", f"origin/design/{slug}", "--", str(rel)],
        ["git", "add", str(rel)],
        ["git", "commit", "-m", f"design: add {slug} design doc"],
        ["git", "push", "origin", "main"],
    ]
    for argv in cmds:
        code, out, err = run_cmd(argv, cwd=repo, env={**os.environ})
        if code != 0:
            # `git commit` may exit 1 if nothing to commit — treat as ok if file already on main
            if argv[1] == "commit" and "nothing to commit" in (out + err).lower():
                continue
            if argv[1] == "checkout" and code != 0:
                return _err(
                    state,
                    f"Merge step failed ({argv}): {err or out}. "
                    f"Ensure branch design/{slug} exists on origin.",
                )
            if argv[1] != "commit":
                return _err(state, f"Command failed ({argv}): {err or out}")
    return {"merge_ran": True, "step": "merged"}


def node_done(state: DesignState) -> dict:
    return {"step": "done"}


def build_design_graph():
    """
    Compile the `/design` LangGraph.

    After merge to `main`, invokes the **queue subgraph** (`build_queue_graph`) to
    ensure labels, parse phases, and open GitHub issues.

    Checkpoints (interrupt):
    - **await_design** — run design agent; write `.dev_cycle/design/<slug>.md`
    - **await_design_fix** — fix validation errors
    - **await_approval** — after close-out push; resume to merge + issues
    """
    g = StateGraph(DesignState)
    g.add_node("resolve_and_load", node_resolve_and_load)
    g.add_node("await_design", node_await_design)
    g.add_node("validate_design", node_validate_design)
    g.add_node("await_design_retry", node_await_design_retry)
    g.add_node("await_approval", node_await_approval)
    g.add_node("merge_to_main", node_merge_to_main)
    g.add_node("run_queue", node_run_queue)
    g.add_node("done", node_done)

    g.add_edge(START, "resolve_and_load")
    g.add_conditional_edges(
        "resolve_and_load",
        route_after_resolve,
        {"await_design": "await_design", "end": END},
    )
    g.add_edge("await_design", "validate_design")
    g.add_conditional_edges(
        "validate_design",
        route_after_validate,
        {
            "await_design_retry": "await_design_retry",
            "await_approval": "await_approval",
        },
    )
    g.add_edge("await_design_retry", "validate_design")
    g.add_edge("await_approval", "merge_to_main")
    g.add_conditional_edges(
        "merge_to_main",
        route_after_merge,
        {"run_queue": "run_queue", "end": END},
    )
    g.add_conditional_edges(
        "run_queue",
        route_after_queue,
        {"done": "done", "end": END},
    )
    g.add_edge("done", END)

    return g.compile(checkpointer=MemorySaver())
