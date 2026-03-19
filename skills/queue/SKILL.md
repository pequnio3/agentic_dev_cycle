---
name: queue
description: >
  Manually create GitHub Issues from approved design docs.
  Use when: re-queueing after editing a design, queueing without immediately building,
  or queueing multiple designs at once.
  Queueing happens automatically at the end of /design — use this skill when you
  want to re-queue after editing a design, queue multiple designs at once, or
  queue without immediately building.
  Use when: "queue this", "re-queue <slug>", or pointing at file(s) in .dev_cycle/design/.
---

# Queue Orchestrator

Read approved design docs and create GitHub Issues labeled `dev-cycle:build`.
Commit the design doc(s) to main so build agents can find them.

> This skill runs automatically at the end of `/design` when a design is approved.
> Use it manually to re-queue after editing a design, queue multiple designs at once,
> or adjust work orders before building.

## Step 1: Read the Design Doc(s)

For each file the user specifies (one or more paths in `.dev_cycle/design/`):

- Read the file
- Confirm it has the structured format (Problem, Solution, Phased Implementation, etc.)
- If still a raw idea (no structured sections), tell the user to run `/design` first

The **slug** is the filename without extension: `.dev_cycle/design/gemini-provider.md` → slug `gemini-provider`.

## Step 2: Determine Work Order Numbers

For each design doc, query existing issues for this slug:

```bash
gh issue list --state all --search "feat(<slug>-" --json title --jq '.[].title' \
  | grep -oE '<slug>-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1
```

New work orders start at `(max + 1)`, or `1` if none exist yet.

## Step 3: Ensure Labels Exist

```bash
gh label create "dev-cycle:build"    --color "0075ca" --description "Work order queued for build"                        2>/dev/null || true
gh label create "dev-cycle:review"   --color "e4e669" --description "Built, PR open"                                     2>/dev/null || true
gh label create "dev-cycle:done"     --color "0e8a16" --description "Merged and complete"                                2>/dev/null || true
gh label create "dev-cycle:decision" --color "d93f0b" --description "Architectural decision or gotcha for future agents" 2>/dev/null || true
```

## Step 4: Create GitHub Issues

For each phase in the design's **Phased Implementation** section (or one issue if
single-phase), create a GitHub Issue:

```bash
gh issue create \
  --title "feat(<slug>-N): <short description of this phase>" \
  --body "$(cat <<'EOF'
Slug: <slug>-N
Branch: dev-<slug>-N
PR: —
Created: <YYYY-MM-DD>
Design: .dev_cycle/design/<slug>.md
Depends on: none   ← or <slug>-<N-1> for phase 2+
Parallel safe: yes ← or no if shared migrations/conflicts

## Idea

<phase content from design doc>

## Context Manifest

<files from design doc, scoped to this phase>
**Complexity:** simple | medium | large
**Relevant decisions:** #N, #N  ← omit line if none

## Scenarios

<BDD scenarios for this phase — omit section if none>

## Plan

<!-- Filled in by build agent -->

## Implementation Notes

- **Branch:** dev-<slug>-N
- **Commits:**
- **Deviations from plan:**
- **Scenarios passing:** <!-- N / N, or N/A -->

## Review

- [ ] Code correctness
- [ ] No spec drift
- [ ] Scenarios pass (if present)
- [ ] No regressions
- [ ] Gate checks pass
EOF
)" \
  --label "dev-cycle:build"
```

Rules:
- Every issue MUST have a Context Manifest
- `Depends on: none` for phase 1; `Depends on: <slug>-<N-1>` for subsequent phases
- `Parallel safe: yes` only if there are no shared DB migrations or file conflicts with sibling work orders
- If Scenarios are present, they are the build agent's **done condition** — the feature is not complete until all pass

## Step 5: Commit and Push to Main

**This is critical.** Build agents run in worktrees branched from main — files not
on main are invisible to them. Commit the design doc so agents can find it.

```bash
# Stage design doc (if not already on main)
git add .dev_cycle/design/<slug>.md

# Commit
git commit -m "design: add <slug> design doc"

git push origin main
```

For multiple design docs:
```bash
git commit -m "design: add <slug-a>, <slug-b>"
```

## Output

Report for each design doc processed:
- Issues created (numbers and titles)
- Dependency chain between them
- Which are immediately buildable (no deps, or deps already in review/done)
- Suggested next command: `/build <slug>` or `/build` to parallelize
