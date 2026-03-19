---
name: build
description: >
  Build queued work orders in isolated worktrees.
  Use when: "build", "build <slug>", "build <slug> --all".
  /build → parallel build all ready items
  /build <slug> → build next item for that slug
  /build <slug> --all → series build all items for that slug
---

# Build Skill

## Invocation (main agent)

### Parse the arguments

- `/build` (no args) → **parallel mode**: build all queued items
- `/build <slug>` → **next mode**: build the next unstarted item for that slug
- `/build <slug> --all` → **series mode**: one agent builds all items for that slug in order

### Parallel mode (`/build`)

1. Query all open issues with `dev-cycle:build` label:
   ```bash
   gh issue list --label "dev-cycle:build" --json number,title,body --limit 100
   ```
2. For each issue, parse the body to extract `Depends on:` and `Parallel safe:` fields.
3. Dependency check — if `Depends on: <dep-slug>-N`, find that issue and check if it has
   label `dev-cycle:review` or `dev-cycle:done`:
   ```bash
   gh issue list --state all --search "feat(<dep-slug>-N)" --json number,labels \
     --jq '.[] | select(.labels[].name | test("dev-cycle:(review|done)"))'
   ```
4. Keep only issues with `Parallel safe: yes` (or sole item for their slug) and met dependencies.
5. Read `.dev_cycle/project.md` for the build model
   (look for the `build` row in the Models table; default: `claude-opus-4-6`).
6. Spawn one **background** build agent per eligible issue:
   ```
   Agent tool:
     isolation: worktree
     run_in_background: true
     prompt: |
       Read .dev_cycle/agents/build_agent.md for your full instructions.
       Work order issue: #<N>
       Model: <model from project.md>
   ```

### Next mode (`/build <slug>`)

1. Query open issues matching `feat(<slug>-` with `dev-cycle:build` label:
   ```bash
   gh issue list --label "dev-cycle:build" --search "feat(<slug>-" --json number,title,body
   ```
2. Take the lowest-numbered eligible issue (dependencies met).
3. Spawn one **background** build agent for it (using model from `project.md`).

### Series mode (`/build <slug> --all`)

1. Query ALL open `dev-cycle:build` issues for this slug, ordered by number:
   ```bash
   gh issue list --label "dev-cycle:build" --search "feat(<slug>-" --json number,title,body \
     --jq 'sort_by(.number)'
   ```
2. Spawn ONE background build agent passing all issue numbers in order:
   ```
   Agent tool:
     isolation: worktree
     run_in_background: true
     prompt: |
       Read .dev_cycle/agents/build_agent.md for your full instructions.
       Work orders (build in series, in order): #<N1> #<N2> ...
       Model: <model from project.md>
   ```
3. The agent handles the dependency chain internally.

### After Build (main agent — run after each agent notification)

When a build agent completes and reports a PR:

```bash
gh issue edit <N> --remove-label "dev-cycle:build" --add-label "dev-cycle:review"
gh issue comment <N> --body "Built on branch dev-<slug>-N. PR: <PR URL>"
```

Report the PR URL to the user.
