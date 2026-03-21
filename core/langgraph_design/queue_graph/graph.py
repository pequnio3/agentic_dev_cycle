"""
Queue workflow: ensure GitHub labels, parse design phases, create `dev-cycle:build` issues.

Invoked by the design graph after the design doc is merged to `main`, or can be run standalone
via `build_queue_graph().invoke(...)`.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from common.issue import generate_issue_body
from common.phases import parse_phased_implementation
from common.shell import run_cmd
from common.types import PhaseSpec
from queue_graph.state import QueueState


def _err_queue(state: QueueState, msg: str) -> dict:
    errs = list(state.get("errors", []))
    errs.append(msg)
    return {"errors": errs, "step": "failed"}


def node_ensure_labels(state: QueueState) -> dict:
    repo = Path(state["repo_root"])
    labels = [
        ("dev-cycle:build", "0075ca", "Work order queued for build"),
        ("dev-cycle:review", "e4e669", "Built, PR open"),
        ("dev-cycle:done", "0e8a16", "Merged and complete"),
        ("dev-cycle:decision", "d93f0b", "Architectural decision or gotcha for future agents"),
    ]
    for name, color, desc in labels:
        run_cmd(
            [
                "gh",
                "label",
                "create",
                name,
                "--color",
                color,
                "--description",
                desc,
            ],
            cwd=repo,
            env={**os.environ},
        )
    return {"labels_ok": True, "step": "labeled"}


def _gh_max_work_order_index(repo: Path, slug: str) -> int:
    code, out, err = run_cmd(
        [
            "gh",
            "issue",
            "list",
            "--state",
            "all",
            "--search",
            f"in:title {slug}-",
            "--json",
            "title",
            "--limit",
            "500",
        ],
        cwd=repo,
        env={**os.environ},
    )
    if code != 0:
        raise RuntimeError(f"gh issue list failed: {err or out}")
    titles = [t["title"] for t in json.loads(out or "[]")]
    pat = re.compile(rf"^{re.escape(slug)}-(\d+):")
    max_k = 0
    for title in titles:
        m = pat.match(title.strip())
        if m:
            max_k = max(max_k, int(m.group(1)))
    return max_k


def node_compute_phases_and_index(state: QueueState) -> dict:
    repo = Path(state["repo_root"])
    slug = state["slug"]
    body = state.get("design_body") or ""
    phases = parse_phased_implementation(body)
    try:
        start = _gh_max_work_order_index(repo, slug) + 1
    except RuntimeError as e:
        return _err_queue(state, str(e))
    return {"phases": phases, "next_work_order_index": start}


def node_create_github_issues(state: QueueState) -> dict:
    repo = Path(state["repo_root"])
    slug = state["slug"]
    phases: list[PhaseSpec] = state.get("phases") or []
    start = int(state.get("next_work_order_index") or 1)
    today = date.today().isoformat()
    urls: list[str] = []
    for i, phase in enumerate(phases):
        n = start + i
        depends = "none" if i == 0 else f"{slug}-{start + i - 1}"
        title = f"{slug}-{n}: {phase['short_title']}"
        body = generate_issue_body(
            slug=slug,
            n=n,
            depends=depends,
            parallel="yes",
            phase=phase,
            today=today,
        )
        code, out, err = run_cmd(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                "dev-cycle:build",
            ],
            cwd=repo,
            env={**os.environ},
        )
        if code != 0:
            return _err_queue(state, f"gh issue create failed: {err or out}")
        url = out.strip()
        if url:
            urls.append(url)
    return {"created_issue_urls": urls, "step": "done"}


def route_after_compute(state: QueueState) -> str:
    if state.get("errors"):
        return "end"
    return "create_github_issues"


def build_queue_graph():
    """Linear queue: labels → compute phases / next index → create issues. No interrupts."""
    g = StateGraph(QueueState)
    g.add_node("ensure_labels", node_ensure_labels)
    g.add_node("compute_phases_and_index", node_compute_phases_and_index)
    g.add_node("create_github_issues", node_create_github_issues)

    g.add_edge(START, "ensure_labels")
    g.add_edge("ensure_labels", "compute_phases_and_index")
    g.add_conditional_edges(
        "compute_phases_and_index",
        route_after_compute,
        {"create_github_issues": "create_github_issues", "end": END},
    )
    g.add_edge("create_github_issues", END)

    return g.compile()
