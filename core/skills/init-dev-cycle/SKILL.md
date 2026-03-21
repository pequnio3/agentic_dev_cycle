---
name: init-dev-cycle
description: >
  Set up the dev cycle for a new project. Generates project.yaml, gates_config.sh,
  and per-agent personality (custom.md) tailored to the project's tech stack.
  Use when: "init dev cycle", "set up dev cycle", "configure dev cycle", or first time
  using this workflow in a project.
---

# Init Dev Cycle Skill

## Invocation (main agent)

Optional: run the executable **`dev-cycle-init-graph`** CLI (from [`core/langgraph_design`](../../langgraph_design/README.md)) for the same checkpoints and validation in LangGraph — useful for orchestrators. The skill below is the human-readable contract.

Spawn a **foreground** init agent to interview the user and generate config files:

```
Agent tool:
  subagent_type: general-purpose
  run_in_background: false
  prompt: <Init Agent Instructions below>
```

Show the agent's output to the user. When the agent is done, remind the user:
- `.dev_cycle/project.yaml` is the structured config (stack, patterns, **`models:`**, gate summaries) — edit it anytime
- `.dev_cycle/gates_config.sh` contains the build/test commands — edit the shell functions
- `.dev_cycle/agents/<name>/custom.md` is **personality** (merged with `base.md` at read time)
- Commit and push after any edits so build agents (which run in worktrees) can find them

---

# Init Agent Instructions

You are setting up the agentic dev cycle workflow for a new project.
Your job is to ask the right questions, then generate three config files that make
all the other skills work correctly for this project.

Do NOT run in a worktree. Work directly in the current repository.

---

## Step 1: Read Existing Config (if any)

**Target path (required):** Write only to **`.dev_cycle/project.yaml`** at the **repository root**
of the project you are configuring (the hidden `.dev_cycle/` directory). The workflow
package keeps the install template in **`core/project.yaml`**; `install.sh` copies it to `.dev_cycle/`.

If `.dev_cycle/` is missing, create it: `mkdir -p .dev_cycle`

Check if `.dev_cycle/project.yaml` already exists and has content. If so, read it —
you may be updating an existing config rather than starting from scratch.

---

## Step 2: Interview the User

Ask the user the following questions. Ask them all at once in a single message
(don't ask one at a time):

1. **What are you building?** Brief description of the project.
2. **What's the tech stack?** (e.g. Flutter + Supabase, React Native + Expo + FastAPI,
   Next.js + Prisma + Postgres, etc.)
3. **How do you run tests?** The exact command(s) to run the test suite.
4. **How do you check for type/lint errors?** (e.g. `flutter analyze`, `npx tsc --noEmit`,
   `pylint`, `eslint`, etc.)
5. **Is there codegen?** (e.g. Dart build_runner, Prisma generate, OpenAPI codegen).
   If yes: what command runs it, and what file changes should trigger it?
6. **What are your key architecture patterns?** Rules agents must follow.
   (e.g. "all DB calls go through repository classes", "use Riverpod for state",
   "feature-first folder structure")
7. **Which model for each agent?** Defaults are shown — override any you want to change.
   Present the table and let the user confirm or replace values:

   | Agent | Default model | Why |
   |-------|--------------|-----|
   | design | claude-opus-4-6 | Architecture decisions need strongest reasoning |
   | build | claude-opus-4-6 | TDD + code generation benefits from best model |
   | review | claude-sonnet-4-6 | Reading + checking, not architecture design |
   | fix | claude-sonnet-4-6 | Targeted edits to existing code |
   | deploy | claude-sonnet-4-6 | Mechanical startup + log monitoring |

   Available models: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`

8. **Anything else agents should know?** Branch naming preferences, code style rules,
   things NOT to do, etc.

Wait for the user's answers before proceeding.

---

## Step 3: Generate `project.yaml`

Overwrite **`.dev_cycle/project.yaml`** with real values from the interview. The install template
is **`core/project.yaml`** — same keys: `project`, `tech_stack_details`, `architecture_patterns`,
`implementation_phases`, `gate_commands` (`iteration` / `pre_pr` / `final`), **`models`** (per agent: `model` + `reason`), `branch_naming`,
`code_style_notes`. Replace `<!-- ... -->` placeholders. **Models** are part of this file (no separate `models.json`).

---

## Step 4: Generate gates_config.sh

Write `.dev_cycle/gates_config.sh` with the correct commands for this project's stack.
Use the exact commands the user provided. Shell functions must match the interface
expected by `.dev_cycle/gates.sh`:

```bash
#!/bin/bash
# Project-specific gate commands — sourced by .dev_cycle/gates.sh
# Edit this file to change build/test commands. Commit and push after changes.

should_run_codegen() {
  # <logic based on user's answer — return 0 to run, 1 to skip>
  # Example: check if model files changed
  # if git diff --name-only HEAD~1 | grep -q 'models/'; then return 0; fi
  return 1
}

run_codegen() {
  <codegen command from user's answer, or echo "no codegen" if none>
}

run_iteration_gate() {
  <test + lint commands from user's answers>
  # Each command should end with "|| return 1" so failures propagate
}

run_pre_pr_gate() {
  run_iteration_gate
  # Add any additional pre-PR checks here
}

run_final_gate() {
  # Add clean build steps here if applicable
  run_iteration_gate
}
```

Be thoughtful about the `should_run_codegen` logic — use git diff to check for
relevant file changes rather than always running codegen.

---

## Step 5: Personality in `custom.md` (per agent)

Each agent uses **`.dev_cycle/agents/<name>/base.md`** (from the tool bundle) plus **`.dev_cycle/agents/<name>/custom.md`** (your personality). Tools merge them: a `## Personality` section is inserted after the title, then the rest of `base.md`.

`<name>`: `design`, `build`, `review`, `fix`, `deploy`, `init`.

Write **project-specific** content in each **`custom.md`**: identity line, stance (e.g. ML architect vs UX-heavy design), and stack context / checks as appropriate — see **`core/agents/init/base.md`** Step 5 for the full checklist.

---

## Step 6: Commit Everything

```bash
git add .dev_cycle/project.yaml .dev_cycle/gates_config.sh .dev_cycle/agents/
git commit -m "dev_cycle: init config for <project name>"
git push origin main
```

**This commit to main is critical.** Build agents run in worktrees branched from main —
they cannot see files that aren't committed and pushed.

Note: the `dev-cycle:decision` label is created automatically by `/complete` on first use —
no manual setup needed.

---

## Output

Report:
- Files generated (project.yaml, gates_config.sh, agents/<name>/{base,custom}.md)
- Summary of the project config (name, stack, gate commands)
- Any questions or ambiguities in the user's answers that should be resolved
- Reminder: edit `.dev_cycle/project.yaml` anytime to refine the config
