from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import git
from langgraph.types import Command

from design_graph.graph import build_design_graph


def _git_repo_root(start: Path) -> Path:
    """Resolve the git work tree root containing `start` (walks parents like `git rev-parse --show-toplevel`)."""
    try:
        repo = git.Repo(start, search_parent_directories=True)
    except git.InvalidGitRepositoryError as e:
        raise SystemExit(
            f"Not a git repository (or any parent): {start.resolve()}\n"
            "Run from inside a clone or pass --repo explicitly."
        ) from e
    wt = repo.working_tree_dir
    if wt is None:
        raise SystemExit("Bare repository: no working tree; pass --repo to the checkout path.")
    return Path(wt).resolve()


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run the dev-cycle /design LangGraph (executable guardrails + interrupts).",
    )
    p.add_argument(
        "raw_input",
        nargs="?",
        help="Path to `.dev_cycle/design/<slug>.md` or a phrase to derive the slug (kebab-case).",
    )
    p.add_argument(
        "--repo",
        type=Path,
        default=None,
        help=(
            "Repository root (default: git work tree root from current directory, "
            "via GitPython — same idea as `git rev-parse --show-toplevel`)."
        ),
    )
    p.add_argument(
        "--thread-id",
        default="dev-cycle-design",
        help="LangGraph thread id for checkpointing (default: dev-cycle-design).",
    )
    p.add_argument(
        "--resume",
        metavar="JSON",
        help="Resume after interrupt: JSON value passed to the interrupted node (e.g. true or {}).",
    )
    p.add_argument(
        "--print-state",
        action="store_true",
        help="Print final state as JSON (paths as strings).",
    )
    args = p.parse_args()

    if not args.resume and not args.raw_input:
        p.error("raw_input is required unless --resume is used")

    repo_root = args.repo.resolve() if args.repo is not None else _git_repo_root(Path.cwd())

    graph = build_design_graph()
    cfg: dict = {"configurable": {"thread_id": args.thread_id}}

    if args.resume:
        resume_val = json.loads(args.resume)
        payload: Command | dict = Command(resume=resume_val)
    else:
        payload = {
            "repo_root": repo_root,
            "raw_input": args.raw_input or "",
            "step": "init",
        }

    out = graph.invoke(payload, cfg)

    if args.print_state:
        printable = _state_to_jsonable(out)
        print(json.dumps(printable, indent=2))

    if out.get("__interrupt__"):
        intr = out["__interrupt__"][0]
        print(
            "\n--- INTERRUPT ---\n"
            f"{intr.value}\n"
            "--- Resume with: ---\n"
            f'  dev-cycle-design-graph --resume true --thread-id {args.thread_id!r}\n',
            file=sys.stderr,
        )
        sys.exit(2)

    if out.get("errors"):
        print("Errors:", out["errors"], file=sys.stderr)
        sys.exit(1)

    print("Done.", out.get("created_issue_urls", []))
    sys.exit(0)


def _state_to_jsonable(state: dict) -> dict:
    out: dict = {}
    for k, v in state.items():
        if k.startswith("__"):
            continue
        if isinstance(v, Path):
            out[k] = str(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out[k] = v
        else:
            try:
                json.dumps(v)
                out[k] = v
            except TypeError:
                out[k] = repr(v)
    return out


if __name__ == "__main__":
    main()
