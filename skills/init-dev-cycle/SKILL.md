---
name: init-dev-cycle
description: >
  Set up the dev cycle for a new project. Generates project.md, gates_config.sh,
  and agent prompts tailored to the project's tech stack.
  Use when: "init dev cycle", "set up dev cycle", "configure dev cycle", or first time
  using this workflow in a project.
---

# Init Dev Cycle Skill

## Invocation (main agent)

Spawn a **foreground** init agent to interview the user and generate config files:

```
Agent tool:
  subagent_type: general-purpose
  run_in_background: false
  prompt: <Init Agent Instructions below>
```

Show the agent's output to the user. When the agent is done, remind the user:
- `.dev_cycle/project.md` is the config — edit it anytime
- `.dev_cycle/gates_config.sh` contains the build/test commands — edit the shell functions
- `.dev_cycle/agents/*.md` are the agent personalities — edit to tune agent behavior
- Commit and push after any edits so build agents (which run in worktrees) can find them

---

# Init Agent Instructions

You are setting up the agentic dev cycle workflow for a new project.
Your job is to ask the right questions, then generate three config files that make
all the other skills work correctly for this project.

Do NOT run in a worktree. Work directly in the current repository.

---

## Step 1: Read Existing Config (if any)

Check if `.dev_cycle/project.md` already exists and has content. If so, read it —
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

## Step 3: Generate project.md

Write `.dev_cycle/project.md` based on the user's answers. Use this structure:

```markdown
# Project Configuration

> Single source of truth for project-specific context.
> All agents read this file. Edit freely — commit and push after changes.

---

## Project

**Name:** <name>
**Description:** <description>
**Stack:** <tech stack summary>

---

## Tech Stack Details

<Detailed description of frameworks, libraries, patterns in use.
Be specific — agents use this to make correct technology decisions.>

---

## Architecture Patterns

<Bulleted list of rules agents must follow. Be explicit and specific.>

---

## Wave Structure

Wave 1: <data layer description for this stack>
Wave 2: <business logic description for this stack>
Wave 3: <UI/presentation description for this stack>

<Adjust to match the actual stack. Some projects may have 2 waves; some may have 4.>

---

## Gate Commands

- **Wave:** <human description of wave gate commands>
- **Pre-PR:** <human description of pre-PR gate commands>
- **Final:** <human description of final gate commands>

See .dev_cycle/gates_config.sh for the actual shell commands.

---

## Models

| Agent | Model | Reason |
|-------|-------|--------|
| design | <model from user's answer> | <their reason or default reason> |
| build | <model from user's answer> | <their reason or default reason> |
| review | <model from user's answer> | <their reason or default reason> |
| fix | <model from user's answer> | <their reason or default reason> |
| deploy | <model from user's answer> | <their reason or default reason> |

---

## Branch Naming

Branch prefix: `dev-`

---

## Code Style Notes

<Any naming, formatting, or file organization rules from the user's answers.>
```

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

run_wave_gate() {
  <test + lint commands from user's answers>
  # Each command should end with "|| return 1" so failures propagate
}

run_pre_pr_gate() {
  run_wave_gate
  # Add any additional pre-PR checks here
}

run_final_gate() {
  # Add clean build steps here if applicable
  run_wave_gate
}
```

Be thoughtful about the `should_run_codegen` logic — use git diff to check for
relevant file changes rather than always running codegen.

---

## Step 5: Generate Agent Prompts

Rewrite each file in `.dev_cycle/agents/` with project-specific personality baked in.
The goal: agents should immediately understand the project context without needing to
reason about it from scratch.

For each agent, take the generic template and prepend a project-specific identity block:

**design_agent.md** — add after "# Design Agent":
```markdown
You are a product designer and technical architect for **<Project Name>**
(<tech stack summary>).
```
Then add a **Tech Stack Context** section before Step 0 that lists:
- Key frameworks and their roles
- State management approach
- Data layer approach
- Any UI patterns to consider in designs

**build_agent.md** — add after "# Build Agent":
```markdown
You are a developer building features for **<Project Name>** (<tech stack summary>).
```
Then add a **Tech Stack Context** section with:
- Key frameworks and patterns
- How to structure new code (feature folders, file naming)
- Common pitfalls to avoid (from architecture patterns)
- Specific wave guidance for this stack (what goes in each wave)

**review_agent.md** — add after "# Review Agent":
```markdown
You are a code reviewer for **<Project Name>** (<tech stack summary>).
```
Then add a **Project-Specific Checks** section with checks tailored to the stack
(e.g. for Flutter: check for widget tests, dispose() calls, const constructors;
for FastAPI: check for N+1 queries, Pydantic schema validation, dependency injection).

**fix_agent.md** — minimal change, just add project name to the opening line.

**deploy_agent.md** — add a **Server Configuration** section with:
- Exact start commands for each server
- Ports used
- Health check URL(s)
- Any environment setup needed before starting

---

## Step 6: Commit Everything

```bash
git add .dev_cycle/project.md .dev_cycle/gates_config.sh .dev_cycle/agents/
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
- Files generated (project.md, gates_config.sh, agents/*.md)
- Summary of the project config (name, stack, gate commands)
- Any questions or ambiguities in the user's answers that should be resolved
- Reminder: edit `.dev_cycle/project.md` anytime to refine the config
