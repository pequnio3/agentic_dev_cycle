# Agentic Dev Cycle

A structured Claude Code workflow for building features with AI agents. Covers the full
lifecycle from raw idea to merged PR, with human approval gates, TDD enforcement, BDD
acceptance criteria, and scoped context loading to keep agents fast and accurate.

Built to drop into any project as a git submodule.

---

## What it does

Instead of asking Claude to "build this feature" and hoping for the best, this workflow
breaks development into phases with a specialist agent for each:

```
/design    raw idea → design doc + BDD scenarios
              ↓ you review and approve  (gate 1)
              → GitHub Issues created automatically
              ↓ you confirm "yes, build"  (gate 2)
/build     GitHub Issues → branch + PR, then automated /review on that branch
/review    same review pass (standalone re-run or after /fix)
              ↓ you validate and merge
/fix       targeted fixes for issues found during validation
/complete  close GitHub Issue, capture decisions and gotchas
```

Two human gates: you approve the design before anything is queued, and confirm
before build agents spin up. Everything in between is automated.

Each agent is scoped to its job. The design agent never writes code. The fix agent never
reads the full codebase. Context is loaded precisely. This keeps quality high and cost low.

---

## Installation

Clone this repo once to your machine, then install into any project:

```bash
git clone https://github.com/pequnio3/agentic_dev_cycle ~/tools/agentic-dev-cycle
bash ~/tools/agentic-dev-cycle/install.sh /path/to/your/project
```

Or from inside your project root:

```bash
bash ~/tools/agentic-dev-cycle/install.sh
```

To **dogfood this repository**, run the same command from the tool repo root — it creates **`.dev_cycle/`** next to **`core/`** (install no longer refuses the tool directory).

The install script:
- Symlinks `.dev_cycle/skills` → the tool's **`core/skills/`** (canonical skill bundle)
- Adds `.claude/skills/dev_cycle` → `.dev_cycle/skills`, plus flat per-skill symlinks under `.claude/skills/` so `/design`, `/build`, etc. work in Claude Code
- Mirrors the same layout under `.cursor/skills/` (Cursor Agent Skills), `.agents/skills/` (Codex + Gemini CLI repo skills), and `.gemini/skills/` (Gemini CLI workspace path)
- Writes / refreshes the workflow block in `AGENTS.md` (Codex + Gemini) — delimited by HTML comments so reinstall can replace it
- Overwrites `.cursor/rules/dev-cycle.mdc` — auto-loaded into every Cursor Composer session
- **Overwrites** bundled templates in `.dev_cycle/` (`gates.sh`, `gates_config.sh`, `project.yaml`, `agents/<name>/{base,custom}.md`, `workflow.md`) so a reinstall picks up tool updates
- Checks for `gh` CLI authentication (required for GitHub Issues integration)
- Adds `.dev_cycle/` and the skill hub directories to `.gitignore`

**Updating the workflow in an existing project:** `git pull` in the tool repo, run `install.sh` again on your project (refreshes skills, templates, and routing), then run **`/init-dev-cycle`** (or `"init dev cycle"`) to regenerate **project-specific** `project.yaml`, `gates_config.sh`, and `agents/<name>/custom.md` (personality).

To preserve old files instead of overwriting, run: `AGENTIC_DEV_CYCLE_NO_OVERWRITE=1 bash …/install.sh`

Then configure for your project. Open Claude Code and run:

```
/init-dev-cycle
```

Or with Codex / Gemini: ask your agent to `"init dev cycle"`.

This interviews you about your tech stack and generates:
- `.dev_cycle/project.yaml` — structured project config (stack, patterns, **`models:`**, gates summary), read by every agent
- `.dev_cycle/gates_config.sh` — your build/test/lint commands
- `.dev_cycle/agents/<name>/custom.md` — personality (merged with `base.md` from the tool)

`.dev_cycle/` is gitignored by default — your workflow state is private.
Teams who want shared workflow state: remove `.dev_cycle/` from `.gitignore` and commit it.

```bash
# If opting into team mode (shared workflow state):
git add .dev_cycle/ AGENTS.md .cursor/rules/dev-cycle.mdc
git commit -m "dev_cycle: init for <project name>"
git push origin main
```

**GitHub CLI requirement:** Work orders are tracked as GitHub Issues. Ensure `gh` is
installed and authenticated before running `/design` or `/build`:

```bash
gh auth login
```

---

## Dogfood on this repo

Versioned skills and templates live under **`core/`** in this repository. Run **`install.sh`** from the repo root (or `bash install.sh /path/to/this/clone`) to create **`.dev_cycle/`** with symlinks and copied templates—the same layout as in any other project. Then use **`/design`**, **`/build`**, etc. on this repo. Edit files under **`core/`** when changing the canonical bundle; reinstall or symlink picks them up.

## Quick reference

| Skill | Model | What it does |
|-------|-------|--------------|
| `/init-dev-cycle` | Sonnet | One-time setup: generates project config and agent prompts |
| `/design <slug>` | Opus | Expands idea → design doc + scenarios → creates GitHub Issues → confirms build |
| `/queue <slug>` | — | Manual: re-queue after edits, batch designs, or queue without building |
| `/build` | Opus | Parallel: one background agent per eligible issue; then `/review` each |
| `/build <slug>` | Opus | Next work order for slug (one background agent), then `/review` |
| `/build <slug> i-j` | Opus | Series for work orders *i*…*j* (e.g. `4-7`): background build → **`/review` to completion** → next build |
| `/build <slug> --all` | Opus | Same series for **all** queued `slug-*` issues |
| `/review <slug>-N` | Sonnet | Review + fixes on branch (auto after `/build`, or manual) |
| `/fix <PR#>` | Sonnet | Iterative fixes on an existing PR branch |
| `/fix <description>` | Sonnet | Standalone bug fix with its own branch and work order |
| `/complete <slug>-N` | — | Closes GitHub Issue, captures decisions as GitHub Issues labeled `dev-cycle:decision` |
| `/deploy` | Sonnet | Dev servers on **current** branch |
| `/deploy #42` or `/deploy 42` | Sonnet | Checkout PR **#42**’s head branch, then run |
| `/deploy model-picker-1` | Sonnet | Checkout **`dev-model-picker-1`**, then run |
| `/deploy dev-foo-2` | Sonnet | Checkout branch **`dev-foo-2`** literally |

Models are defaults. Override per-agent under `models:` in `.dev_cycle/project.yaml`.

**Optional — executable `/design` and `/init-dev-cycle` graphs:** [`core/langgraph_design/README.md`](core/langgraph_design/README.md) packages [LangGraph](https://github.com/langchain-ai/langgraph) state machines with the same checkpoints as the skills. **`install.sh` runs `python3 -m pip install -e core/langgraph_design`** so `dev-cycle-design-graph` and `dev-cycle-init-graph` are available (set `AGENTIC_DEV_CYCLE_SKIP_PIP=1` to skip). Use when you want deterministic guardrails and `interrupt`/`resume` instead of prompt-only orchestration.

---

## Scenarios

### Starting a new feature

Write a rough idea — as informal as a few sentences. You don't need to specify
implementation details. Run `/design`:

```
/design add a dark mode toggle
```

The design agent reads your project config, interrogates the idea from UX, technical,
and edge-case angles, and returns a structured design doc with BDD scenarios. Review it,
iterate if needed, then approve:

> "looks good"

The design skill automatically creates GitHub Issues and asks before starting:

```
Created 2 GitHub Issue(s) for dark-mode:
- #42 dark-mode-1: Theme tokens + storage layer  [dev-cycle:build]
- #43 dark-mode-2: UI components + toggle  [dev-cycle:build]

Ready to build? (yes / build dark-mode-1 only / not yet)
```

Say `yes` — build agents spin up in isolated worktrees, implement with TDD, ensure all
scenarios pass, and create PRs. You get notified when done.

---

### Working on a BE-heavy feature with no user-facing UI

BDD scenarios still apply — they just describe API contracts and data invariants
rather than user flows:

```gherkin
Scenario: Alignment chain composition
  Given documents A and B are aligned
  And documents B and C are aligned
  When a point is projected from A to C
  Then the result uses the composed A→B·B→C transform
  And the result matches a direct A→C calibration within 2px
```

The design agent detects that this is a backend/data feature and writes scenarios at
the appropriate level automatically. You can guide it by describing the feature in
technical terms in your raw idea.

---

### Iterating on a design before building

The design agent is resumable. Run `/design`, review the output, give feedback,
and the same agent iterates — the worktree persists between turns:

```
/design payment-integration
```

Review the draft. If you want changes:

> "The refund flow needs to handle partial refunds, not just full. Also split this
> into two work orders — payment capture first, refund second."

The agent updates the design doc in the same session. When satisfied:

> "looks good, queue it"

The agent commits and the main session creates the GitHub Issues.

---

### Fixing bugs found during validation

After `/build`, the PR already exists and automated `/review` updates that branch.
Build agents are instructed to include **How to test (manual QA)** steps and a **very rough
estimated LLM token** table (build + review) in the PR body — use those as a starting
checklist; they are not exact usage reports.

Check out the PR branch and test manually. If you find
issues, describe them to `/fix`:

```
/fix #23
```

The fix agent checks out the PR branch and waits for you to describe issues. Describe
them one at a time in plain language:

> "The dropdown closes when you click the scrollbar inside it"

The agent reads only the relevant files, makes the minimal fix, commits, and confirms.
Describe the next issue or say "done" to push and update the PR.

---

### Fixing a standalone bug (not tied to an open PR)

```
/fix the session expires silently without showing the user a message
```

The agent creates its own branch and fixes the bug iteratively. When you say "done",
it creates a PR.

---

### Running multiple features in parallel

```
/build
```

No arguments — the build skill queries all open `dev-cycle:build` issues with
`Parallel safe: yes` and met dependencies, and spawns a background build agent for
each simultaneously.

You get notified as each finishes. While they run you can keep working.

---

### Features with dependencies (chained work orders)

If Phase 2 builds on Phase 1, the issue body marks the dependency:

```
Depends on: auth-scaffold-1
```

The build skill checks this before spawning. Phase 2 won’t start until Phase 1’s issue
is `dev-cycle:review` or `dev-cycle:done`. For **same-slug** chains (**A-1**, **A-2**, **A-3**),
later phases **branch from the predecessor’s remote branch** (`origin/dev-A-1`, then
`origin/dev-A-2`); every PR still **opens against `main`**. Merge earlier PRs first (or
rebase after they land). If the predecessor is already merged, the next branch starts
from **`main`**.

---

### Deploying a PR (or feature branch) for local testing

```
/deploy #23
/deploy 23              ← same as #23 (digits-only = PR number)
/deploy model-picker-1  ← branch dev-model-picker-1
/deploy dev-foo-2       ← literal branch name
/deploy                 ← current checkout
```

Checks out the target branch, starts dev servers (using context from `project.yaml` and `gates_config.sh`),
and monitors logs. Startup errors are auto-fixed. While it's running you can say:

- `"logs"` — show recent server output
- `"restart backend"` — restart just the backend
- `"stop"` — shut everything down

---

### Updating the workflow

```bash
cd ~/tools/agentic-dev-cycle
git pull
bash install.sh /path/to/your/project   # safe to re-run, skips existing config files
```

With **`AGENTIC_DEV_CYCLE_NO_OVERWRITE=1`**, `install.sh` skips existing `project.yaml`,
`gates_config.sh`, and **`agents/*/custom.md`** (your personality). By default, reinstall
refreshes **`base.md`** and **`project.yaml`** templates from the tool unless skipped the same way.

---

## Key concepts

### GitHub Issues as queue

Work orders are GitHub Issues, not files. Labels track state:

| Label | Meaning |
|-------|---------|
| `dev-cycle:build` | Queued — ready for a build agent |
| `dev-cycle:review` | Built — PR open, awaiting merge |
| `dev-cycle:done` | Merged and complete |
| `dev-cycle:decision` | Architectural decision or gotcha for future agents |

Issue titles follow the pattern `<slug>-N: <short description>` (labels already mark the work-order type). The issue body
contains the full work order: Idea, Context Manifest, Scenarios, Plan, and Implementation Notes.

This means your queue is always visible on GitHub, shareable with your team, and you can
edit work orders directly in the GitHub UI before building.

### BDD Scenarios

The design agent drafts BDD acceptance criteria as part of every design doc.
They're written at the appropriate level for the feature:

- **UI features** — user-facing Given/When/Then flows
- **API features** — request/response contract scenarios
- **Data features** — invariant and cascade scenarios
- **Infrastructure / refactor** — skipped, no behavioral contract to specify

Scenarios become the build agent's done condition. The review agent won't approve
a PR with failing scenarios. This closes the spec-drift loop structurally —
if scenarios pass, the feature matches the design.

Uncertain scenarios (where the correct behavior requires a product decision) are
flagged in Open Questions rather than written vaguely. A missing scenario is better
than a wrong one.

### Worktree isolation

Build agents run in isolated git worktrees on their own branches. They can't break
your working tree and you can keep using Claude Code while they run in the background.

This requires that all files agents need are committed to main before building.
Any time you edit `project.yaml` or prompts, commit and push before running `/build`.

### The 35-minute rule

Agent quality degrades sharply after ~35 minutes of active work. The workflow enforces
small features through **implementation phases** — each phase should be completable in under
35 minutes. If a phase would exceed this, the build agent splits it or reports back.

### Scoped context loading

Agents read only what they need. The Context Manifest in each GitHub Issue lists exactly
which files and docs the build agent should read. The fix agent reads only bug reports
and affected files — not the full codebase. This reduces token cost by 30-40% and
improves accuracy by keeping the context relevant.

### Decisions as GitHub Issues

Every time a feature is completed, the `/complete` skill extracts key decisions and
gotchas into GitHub Issues labeled `dev-cycle:decision`. The design agent scans these
issue titles at design time and links relevant ones in the Context Manifest. Build agents
follow those pointers directly — no searching, no guessing.

This is institutional memory — past discoveries (like "we use `_apply_migrations`, never
recreate tables") prevent agents from repeating mistakes. Each decision issue is
self-contained and fully understandable on its own.

---

## Configuration

All project-specific config lives in `.dev_cycle/project.yaml`. Edit it directly or
re-run `/init-dev-cycle` to regenerate it. Key sections:

| Section | What it controls |
|---------|-----------------|
| Tech Stack Details | How agents structure code and make technology choices |
| Architecture Patterns | Rules agents must follow (e.g. repository pattern, state management) |
| Implementation phases | How work is split into phases for your stack (`implementation_phases` in `project.yaml`) |
| Models | Which Claude model runs each agent type |
| Gate Commands | Human-readable description of what `gates.sh` runs |

After editing, commit and push so build agents (in worktrees) pick up the changes.

### Changing model assignments

Edit `models:` in `.dev_cycle/project.yaml`:

```markdown
| Agent  | Model               |
|--------|---------------------|
| design | claude-opus-4-6     |
| build  | claude-opus-4-6     |
| review | claude-sonnet-4-6   |
```

Available: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`

### Changing gate commands

Edit `.dev_cycle/gates_config.sh`. The file has three functions:

```bash
run_iteration_gate()   # run after each implementation phase (`gates.sh iteration`)
run_pre_pr_gate() # run before creating PR
run_final_gate()  # run after merge (clean build check)
```

---

## Directory layout

After install and init, your project will have:

```
~/tools/agentic-dev-cycle/   ← the tool (clone once, use across projects)
  core/
    skills/                  ← skill definitions (SKILL.md per command)
    ...                      ← templates and generic docs (versioned bundle)
  .dev_cycle/                ← after install.sh: symlinks + copies (gitignored by default)

AGENTS.md                    ← workflow routing for Codex + Gemini (committed)

.cursor/
  rules/
    dev-cycle.mdc            ← auto-loaded into every Cursor Composer session (committed)
  skills/                    ← symlinks created by install (gitignored): dev_cycle/, design/, ...

.claude/
  skills/                    ← symlinks (gitignored): dev_cycle/ → .dev_cycle/skills, plus per-skill

.agents/skills/              ← same pattern for Codex CLI (gitignored)
.gemini/skills/              ← same pattern for Gemini CLI (gitignored)

.dev_cycle/                  ← your project's workflow state (gitignored by default)
  skills -> .../core/skills   ← symlink to the tool bundle (created by install.sh)
  project.yaml               ← project config + models (generated by /init-dev-cycle)
  gates.sh                   ← generic gate runner
  gates_config.sh            ← your build/test commands
  workflow.md                ← this workflow's documentation
  agents/                    ← base.md (from tool) + custom.md (personality from /init-dev-cycle)
    design/base.md custom.md
    build/base.md custom.md
    review/ fix/ deploy/ init/ …
  design/                    ← draft scratch space for design agent output

GitHub Issues (work order queue):
  dev-cycle:build            ← ready to build
  dev-cycle:review           ← PR open, awaiting merge
  dev-cycle:done             ← merged and complete
```

`.dev_cycle/` is hidden and gitignored by default. This keeps your workflow state
private. Teams who want to share workflow state (design docs, decisions log)
can remove `.dev_cycle/` from `.gitignore` and commit it.

---

## Tips

**Keep features small.** If a feature would take more than 35 minutes of agent work,
split it during design. Two small work orders build faster and with higher quality
than one large one.

**The idea is the input.** Be specific in your raw ideas — vague ideas produce vague
designs. Include constraints, non-goals, and known edge cases if you have them.

**Review the scenarios critically.** Vague scenarios reveal underspecified design.
If the design agent writes a weak scenario, the design itself needs more thought.
Push back before queuing — it's cheaper to fix the spec than the code.

**Past decisions inform new designs.** The design agent scans `dev-cycle:decision` issues
before designing. Past gotchas (like "the session token must be rotated on every auth action,
not just login") are automatically surfaced for relevant features.

**Queue state is on GitHub.** Work order status and decisions live in GitHub Issues — no
files to commit when transitioning between build/review/done. Only config changes
(`project.yaml`, `gates_config.sh`, `agents/`) need committing.

**Never skip `/complete`.** Closing the issue and extracting decisions takes 30 seconds
and saves hours of future debugging. The decisions log is only as good as the discipline
to maintain it.
