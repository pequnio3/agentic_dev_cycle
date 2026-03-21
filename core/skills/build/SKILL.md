---
name: build
description: >
  Build queued work orders in isolated worktrees, then run /review on each result.
  Use when: "build", "build <slug>", "build <slug> i-j", "build <slug> --all".
  /build → parallel build all ready items
  /build <slug> → next single item for that slug (one background agent)
  /build <slug> i-j or --all → series: main orchestrates one fresh build agent per issue, in order
---

# Build Skill

## Role split (main session vs build agents)

- **Build subagents** run in **isolated worktrees** with `run_in_background: true`. They implement the work order and, when done, **report back** to the main session (branch, PR URL, gates, scenarios, concerns) via the normal Agent-tool completion path.
- **You (main Claude)** stay in the primary session: you **do not** implement builds yourself here. You **spawn** build agents. When one **finishes**, you run **After Build**: update the issue (labels + comment), then **chain `/review`** (review subagent — typically **foreground** — must **run to completion**). Only **after `/review` finishes** may you **spawn the next background build** for the following work order in a **series**. Apply the **context gate** before that next spawn. In **parallel** mode, handle each build’s completion the same way (**review to completion** for that issue); there is no “next in series” ordering, but still do not skip **`/review`** unless the user asked for build-only.

## Invocation (main agent)

### Parse the arguments

| Input | Mode |
|-------|------|
| `/build` *(no args)* | **Parallel** — one **background** agent per eligible issue |
| `/build <slug>` | **Next** — lowest eligible `<slug>-*` work-order issue, one **background** agent |
| `/build <slug> i-j` | **Orchestrated series** — work orders `<slug>-i` through `<slug>-j` inclusive *(i, j = numeric work-order indices; see below)* |
| `/build <slug> --all` | **Orchestrated series** — every open `dev-cycle:build` issue for `<slug>`, ordered by work-order index |

**Slug vs range:** The last token must be **`i-j`** — two non-negative integers with a hyphen (e.g. `4-7`, `10-12`; **any** valid range, not only 1–3). `i` and `j` are the work-order indices `k` from issue titles `<slug>-k: …`. Require `i ≤ j`. Everything before that token is `<slug>` (may contain hyphens, e.g. `auth-core 2-5` → slug `auth-core`, range 2–5).

**Legacy:** Do **not** pass multiple issue numbers to a **single** build agent. Series work is always **one build subagent per issue**, then **chained `/review` to completion**, then **you** spawn the **next** background build.

---

### Resolve issues for a slug

```bash
gh issue list --label "dev-cycle:build" --search "in:title <slug>-" \
  --json number,title,body --limit 200
```

From each title `<slug>-<k>: …`, parse **work-order index** `<k>`: take the substring before the first `:`, then the last `-<digits>` suffix is `<k>` (the rest is `<slug>`; slugs may contain hyphens).

- **Range mode:** keep issues where `i ≤ k ≤ j`.
- **`--all` mode:** keep all matches for `<slug>`.
- **Sort** by `<k>` ascending (not by GitHub issue #).
- **Dependencies:** drop any issue whose `Depends on:` line references a work order that is **not** yet labeled `dev-cycle:review` or `dev-cycle:done` (same rules as parallel mode). If some indices in `i-j` are ineligible, **skip** them and tell the user which were skipped and why.

---

### Parallel mode (`/build`)

1. Query all open issues with `dev-cycle:build` label:
   ```bash
   gh issue list --label "dev-cycle:build" --json number,title,body --limit 100
   ```
2. For each issue, parse the body for `Depends on:` and `Parallel safe:`.
3. Dependency check — if `Depends on: <dep-slug>-N`, that dependency must be `dev-cycle:review` or `dev-cycle:done`:
   ```bash
   gh issue list --state all --search "in:title <dep-slug>-N:" --json number,labels \
     --jq '.[] | select(.labels[].name | test("dev-cycle:(review|done)"))'
   ```
4. Keep only issues with `Parallel safe: yes` (or sole item for their slug) and met dependencies.
5. Read `.dev_cycle/project.yaml` for the build model (`models.build.model`; default: `claude-opus-4-6`).
6. Spawn one **background** build agent **per** eligible issue:
   ```
   Agent tool:
     isolation: worktree
     run_in_background: true
     prompt: |
       Read `.dev_cycle/agents/build/base.md` and `custom.md` (merged at runtime).
       Work order issue: #<N>
       Model: <model from project.yaml>
   ```

---

### Next mode (`/build <slug>`)

1. List issues as in “Resolve issues for a slug” (no range filter).
2. Take the **lowest** `<k>` that is dependency-eligible.
3. Spawn **one background** build agent for that GitHub issue `#N`.

---

### Orchestrated series mode (`/build <slug> i-j` or `/build <slug> --all`)

**Goal:** Work orders run **in series** (by `<k>`): each order gets a **new** build subagent (fresh context), builds run **in the background** (`run_in_background: true`). **Pipeline per issue:** background **build** completes → main runs **After Build** (labels + comment) → main **chains `/review`** and waits until the **review subagent finishes** → **context gate** → **then** spawn the **next** background build for the following planned issue. **Never** start the next series build until **`/review` for the current issue has fully completed** (unless user asked **build-only**).

1. Build the **ordered** target list `#N1, #N2, …` (all indices in range or `--all`, sorted by `<k>`). This is the **series plan**, not necessarily all eligible at once.
2. If the plan is empty, say so and stop.
3. Read `.dev_cycle/project.yaml` for the build model.
4. **Series loop:**
   - From the plan, pick the **next** issue that is **dependency-eligible** *now* (re-check `Depends on:` / labels against GitHub if unsure). If none left in the plan, summarize and stop.
   - **Context gate (main session, before spawn)** — same rules as before: if **you** are context-starved, stop after the current handoff and tell the user how to resume (`/build <slug> <next_k>-<j>`, `/compact`, new session, etc.).
   - Spawn **one** **background** build agent for that issue only:
     ```
     Agent tool:
       isolation: worktree
       run_in_background: true
       prompt: |
         Read `.dev_cycle/agents/build/base.md` and `custom.md` (merged at runtime).
         Work order issue: #<Nm>
         Implement ONLY this issue. If your prompt ever listed multiple issues, that was a mistake — one issue per invocation.
         Model: <model from project.yaml>
     ```
   - **Stop** — do not spawn another series build in the same turn. When this build agent **notifies completion**, run **After Build** for `#Nm`, then **invoke the full `review` skill** and wait until that **review** subagent **returns**. Apply the **context gate**. **Only then** (next turn if needed) spawn the **next** background build for the following planned issue — **not** before **`/review`** completes.

5. When every planned issue has been built (and reviewed per policy), summarize all PRs and review outcomes.

**Why only one background build per series at a time:** Preserves order, avoids two
worktrees racing the same slug, and ensures **`origin/dev-<slug>-k`** exists (or predecessor
is merged) before the next agent runs **`git checkout -B … origin/dev-<slug>-(k-1)`** for
stacked same-slug chains.

---

### After Build (main agent — after each build agent finishes)

When a build agent completes and reports branch + PR URL:

1. **GitHub labels and comment** — transition the issue out of the build queue (before or as you start review):

```bash
gh issue edit <N> --remove-label "dev-cycle:build" --add-label "dev-cycle:review"
gh issue comment <N> --body "Built on branch dev-<slug>-<k>. PR: <PR URL>"
```

2. **Chain `/review`** — run the **`review` skill** for this issue. Pass:
   - `Feature branch: dev-<slug>-<k>` (from work order / agent report)
   - `PR: <URL>`
   Use the review model from `.dev_cycle/project.yaml`. **One review at a time.** Let the review subagent **finish completely** before any **next** step (e.g. spawning the **next** series build).

3. Report PR URL and review verdict to the user.

If the user asked for **build only**, skip step 2 and only run the `gh` lines + PR report.

**Parallel mode:** completions may arrive in any order; for **each** notification run **After Build** end-to-end (**review to completion** unless build-only).

**Series mode:** the **next** background build for the queue **must not** start until step 2 (**`/review`**) has **completed** for the current issue.

---

### Summary

| Mode | Build agents | Subagent context |
|------|----------------|------------------|
| Parallel | Many, **background** | One issue each, fresh per spawn |
| Next | One, **background** | Fresh |
| Series (`i-j` / `--all`) | Many, **one after another**, each **background** | Build completes → After Build → **`/review` to completion** → then spawn **next** background build |
