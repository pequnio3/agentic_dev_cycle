# Dev-cycle LangGraph

Executable orchestration for dev-cycle workflows: **`/design`** ([`../skills/design/SKILL.md`](../skills/design/SKILL.md)) and **`/init-dev-cycle`** ([`../skills/init-dev-cycle/SKILL.md`](../skills/init-dev-cycle/SKILL.md)). This package encodes **deterministic** steps (slug resolution, `project.yaml` model lookup, validation, `git`/`gh` commands) and **human checkpoints** (`interrupt`) where a coding agent or you must act.

## Why use this

- **Guardrails** — the design graph will not merge to `main` or create GitHub issues until prior steps succeed; the init graph checks that `project.yaml`, `gates_config.sh`, and agent prompts look complete before finishing.
- **Same protocol as the skills** — checkpoints mirror the skills: e.g. draft design → validate → approve after close-out → merge → **queue** (labels + issues); init → validate generated config.
- **Composable queue** — GitHub label bootstrap, phased parsing, and `gh issue create` live in **`build_queue_graph()`** (`queue_graph` package); the design graph calls it after merge.
- **Orchestrator-friendly** — an outer agent (Cursor, Claude Code, etc.) can run `invoke` / `resume` with a stable `thread_id` instead of hoping the model follows a long markdown checklist.

## Package layout

| Package | Role |
|--------|------|
| `design_graph` | `/design` graph: slug resolution, validation, interrupts, merge, then queue. |
| `init_graph` | `/init-dev-cycle` graph: load bundled `init_graph/prompt.md`, interrupt for interview, **resume with JSON** (`project`, `gates_config_sh`, `agents`), apply to disk, validate `project.yaml` + agent dirs. |
| `queue_graph` | Standalone queue subgraph: GitHub labels → phased parsing → `gh issue create`. |
| `common` | Shared types (`PhaseSpec`), issue body template, phased parsing, subprocess helpers, `read_agent` / `Agent`, `project.yaml` loading, slug/model resolution — reusable by future skill graphs. |

## Install

**Recommended:** run the repo’s **`install.sh`** from your project root — it copies templates, links skills, and runs **`python3 -m pip install -e core/langgraph_design`** (unless `AGENTIC_DEV_CYCLE_SKIP_PIP=1`).

Manual install from the repo root:

```bash
python3 -m pip install -e ./core/langgraph_design
```

Requires `gh` authenticated (`gh auth login`) and `git` with push access for the target repo (design / queue paths). Init only needs a normal git checkout.

## CLI — `/design`

```bash
# Start (derive slug from phrase → `.dev_cycle/design/<slug>.md`)
# Default --repo is the git work tree root for your current directory (not necessarily cwd).
dev-cycle-design-graph "my feature name"

# Or pass a design file path / explicit repo root
dev-cycle-design-graph .dev_cycle/design/my-slug.md --repo /path/to/app
```

When the graph **interrupts**, it prints a checkpoint payload to stderr and exits `2`. Resume with:

```bash
dev-cycle-design-graph --resume true --thread-id dev-cycle-design
```

Use the **same** `--thread-id` for every `resume` in that run.

## CLI — `/init-dev-cycle`

```bash
# Configure the project in the current git repo (default repo = `git rev-parse` root)
dev-cycle-init-graph

dev-cycle-init-graph --repo /path/to/app --thread-id dev-cycle-init
```

Resume after interrupt (pass the **init submit JSON** as one shell argument):

```bash
dev-cycle-init-graph --resume "$(jq -c . submit.json)" --thread-id dev-cycle-init
```

## Checkpoints (`interrupt`)

### Design graph

| Checkpoint | You / agent action |
|------------|-------------------|
| `await_design` | Run the design agent using **`agent_instructions`** (merged `agents/design/base.md` + `custom.md`) plus **`design_file`** / **`model`**. |
| `await_design_fix` | Fix validation errors listed in the payload; re-run resume. |
| `await_approval` | Ensure close-out (commit + push to `design/<slug>`) is done; then resume to merge and open issues. |

### Init graph

| Checkpoint | You / agent action |
|------------|-------------------|
| `await_init` | Run the init agent using **`agent_instructions`** (bundled **`init_graph/prompt.md`**). **Resume** with JSON: **`project`**, **`gates_config_sh`**, **`agents`** — the graph writes files and validates. |
| `await_init_fix` | Fix **`validation_errors`**; **resume** with an updated JSON object (same schema). |

## Python API

### Design graph (`build_design_graph`)

```python
from pathlib import Path
from langgraph.types import Command
from design_graph.graph import build_design_graph

graph = build_design_graph()
cfg = {"configurable": {"thread_id": "my-thread"}}

out = graph.invoke(
    {"repo_root": Path("/path/to/repo"), "raw_input": "my-slug", "step": "init"},
    cfg,
)
if out.get("__interrupt__"):
    out = graph.invoke(Command(resume=True), cfg)
```

### Queue graph only (`build_queue_graph`)

Use this if you already have a merged design doc on `main` and only need to open issues (same steps as the tail of `/design`):

```python
from pathlib import Path
from queue_graph import build_queue_graph

q = build_queue_graph()
out = q.invoke({
    "repo_root": Path("/path/to/repo"),
    "slug": "my-feature",
    "design_body": Path("/path/to/repo/.dev_cycle/design/my-feature.md").read_text(),
})
# out["created_issue_urls"], or out["errors"]
```

### Init graph (`build_init_graph`)

```python
from pathlib import Path
from langgraph.types import Command
from init_graph.graph import build_init_graph

graph = build_init_graph()
cfg = {"configurable": {"thread_id": "my-init-thread"}}

out = graph.invoke(
    {"repo_root": Path("/path/to/repo"), "step": "init"},
    cfg,
)
if out.get("__interrupt__"):
    submit = {
        "project": {...},  # mapping → .dev_cycle/project.yaml
        "gates_config_sh": "#!/bin/bash\n...",
        "agents": {
            "design": "...",
            "build": "...",
            "review": "...",
            "fix": "...",
            "deploy": "...",
        },
    }
    out = graph.invoke(Command(resume=submit), cfg)
```

## What is *not* automated

- **LLM design work** — still done by your agent using merged `design` prompts; this graph only **gates** it.
- **LLM init work** — interview runs in your agent using bundled **`init_graph/prompt.md`**; you **resume** with structured JSON and the graph **applies** it to `.dev_cycle/` then validates (it does not run `git commit` for you).
- **Models** — `parse_design_model(repo)` reads **`.dev_cycle/project.yaml`** ``models.design``, then legacy `models.json` or old `project.md`.
- **Issues vs personalities** — repo-wide stance lives in **`agents/*/custom.md`**. Optional **Agent focus** section in each GitHub issue body is for **one-off** emphasis on that work order; you usually do not paste full agent prompts into issues.
- **Phased implementation parsing** — best-effort: `## Phased Implementation` with `###` subsections becomes multiple issues; otherwise one issue is created from the doc.
- **Exact match to hand-edited issue bodies** — bodies follow [`../issue_template.md`](../issue_template.md); tune `ISSUE_BODY_TEMPLATE` in `common/issue.py` if your template diverges.

## Relationship to the Cursor skills

Skills under [`../skills/`](../skills/) remain the **human-readable contracts**. This package is an optional **machine-executable** version: keep them in sync when you change queue rules, issue title format, or init validation heuristics.
