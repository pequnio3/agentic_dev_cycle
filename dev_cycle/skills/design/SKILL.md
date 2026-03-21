---
name: design
description: >
  Expand a raw idea into a structured design doc ready for development.
  Use when: "design this", "expand this idea", "design <slug>", or pointing at a
  file in .dev_cycle/design/.
  On approval, automatically creates GitHub Issues and asks if you want to build.
---

# Design Skill

## Invocation (main agent)

When this skill is invoked:

1. Derive the slug from the argument:
   - If a file path is given (`.dev_cycle/design/foo-bar.md`), slug = `foo-bar`
   - If a description is given ("knowledge bank"), slug = kebab-cased: `knowledge-bank`
   - The design file path is always `.dev_cycle/design/<slug>.md`

2. Read `.dev_cycle/project.md` to get the model for the design agent
   (look for the `design` row in the Models table; default: `claude-opus-4-6`).

3. Spawn a **foreground** design agent in an isolated worktree:
   ```
   Agent tool:
     subagent_type: general-purpose
     isolation: worktree
     run_in_background: false
     prompt: |
       Read .dev_cycle/agents/design_agent.md for your full instructions.
       Design file: .dev_cycle/design/<slug>.md
       Slug: <slug>
       Model: <model from project.md>
   ```
   The agent returns a draft + open questions. Show the output to the user.

4. **Iterate**: when the user gives feedback, **resume** the same agent (pass its
   returned ID). Do NOT spawn a new agent — the worktree must persist across turns.

5. **Close out**: when the user approves ("looks good", "ship it", "queue it", "build it"),
   resume the agent one final time with: `"Close out: commit the design file and push."`

6. **Merge to main**: after the agent pushes its branch, bring the design file to main:
   ```bash
   git fetch origin
   git checkout origin/design/<slug> -- .dev_cycle/design/<slug>.md
   git add .dev_cycle/design/<slug>.md
   git commit -m "design: add <slug> design doc"
   git push origin main
   ```
   If ambiguous, copy the file content and commit directly.

7. **Create GitHub Issues** (automatic — no user action needed):

   Read the approved design doc and create one GitHub Issue per phase from the
   design's Phased Implementation section (or one issue if single-phase).

   **Determine work order numbers** — query existing issues for this slug:
   ```bash
   gh issue list --state all --search "in:title <slug>-" --json title --jq '.[].title' \
     | grep -oE '<slug>-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1
   ```
   New work orders start at `(max + 1)`, or `1` if none exist.

   **Ensure labels exist**:
   ```bash
   gh label create "dev-cycle:build"    --color "0075ca" --description "Work order queued for build"                        2>/dev/null || true
   gh label create "dev-cycle:review"   --color "e4e669" --description "Built, PR open"                                     2>/dev/null || true
   gh label create "dev-cycle:done"     --color "0e8a16" --description "Merged and complete"                                2>/dev/null || true
   gh label create "dev-cycle:decision" --color "d93f0b" --description "Architectural decision or gotcha for future agents" 2>/dev/null || true
   ```

   **Create the issue** using `dev_cycle/issue_template.md` as the body structure:
   ```bash
   gh issue create \
     --title "<slug>-N: <short description of this phase>" \
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
   - `Depends on: none` for phase 1; `Depends on: <slug>-<N-1>` for subsequent phases
   - `Parallel safe: yes` only if no shared DB migrations or file conflicts with siblings

   Note the issue URL and number from the output.

   **Also commit the design doc to main** (no work order files to commit):
   ```bash
   git fetch origin
   git checkout origin/design/<slug> -- .dev_cycle/design/<slug>.md
   git add .dev_cycle/design/<slug>.md
   git commit -m "design: add <slug> design doc"
   git push origin main
   ```
   (Skip if already done in step 6.)

8. **Confirm before building**: Show the user what was created and ask if they want
   to build now:

   ```
   Created N GitHub Issue(s) for <slug>:
   - #<N1> <slug>-1: <phase 1 description>  [dev-cycle:build]
   - #<N2> <slug>-2: <phase 2 description>  [dev-cycle:build]

   Ready to build? I'll spawn build agents in isolated worktrees.
   (yes / build <slug>-1 only / not yet)
   ```

   **If the user confirms** (yes, build it, go, start):
   - Follow the build skill logic from `.dev_cycle/skills/build/SKILL.md`
   - Spawn background build agents for all eligible issues
   - Report PR URLs as agents complete

   **If the user defers** (not yet, later, no):
   - Acknowledge and stop: "Issues are queued. Run `/build <slug>` when you're ready."

   **If the user wants a subset** (build 1 only, just the first):
   - Spawn only the requested issue's build agent
---

> **Note:** `/queue` still exists as a standalone skill for cases where you want to
> queue without building, re-queue after editing a design, or queue multiple designs
> at once. The automatic queueing above follows the same logic.
