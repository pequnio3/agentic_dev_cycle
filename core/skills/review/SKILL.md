---
name: review
description: >
  Review a feature branch against the spec, check for quality issues, verify tests.
  Use when: "review this", "review feature", or after a build completes.
  Model: Sonnet — review is reading + checking, not architecture design.
---

# Review Skill

## Invocation (main agent)

When this skill is invoked:

1. Determine the issue number from the argument:
   - If an issue number is given (`#N` or `N`), use it directly
   - If a slug is given (`slug-N`), resolve the issue number:
     ```bash
     gh issue list --state all --search "in:title <slug>-N:" --json number,title \
       | jq '.[0].number'
     ```

2. Read `.dev_cycle/project.yaml` to get the model for the review agent
   (look for the `review` row in the Models table; default: `claude-sonnet-4-6`).

3. Spawn a **foreground** review agent in the project repo (no new worktree). The agent
   checks out the feature branch when you pass **`Feature branch:`** (required after `/build`;
   optional for a manual `/review` when the user is already on that branch):
   ```
   Agent tool:
     subagent_type: general-purpose
     run_in_background: false
     prompt: |
       Read `.dev_cycle/agents/review/base.md` and `custom.md` (merged at runtime).
       Work order issue: #<N>
       Feature branch: dev-<slug>-<N>
       PR: <PR URL if known>
       Model: <model from project.yaml>
   ```

4. After the review agent finishes (it updates the branch with fixes and pushes as needed):
   ensure the issue has label `dev-cycle:review` and not `dev-cycle:build`:
   ```bash
   gh issue edit <issue-N> --remove-label "dev-cycle:build" --add-label "dev-cycle:review" 2>/dev/null || true
   ```

   (Idempotent — `/build` may already have applied this label when chaining.)

   The PR should already exist from the build agent and link to the issue; the review agent
   adds commits on the same branch.

5. Show the agent's output to the user. If the verdict is `changes-needed`, the user
   can run `/fix` to address issues, then re-run `/review`.
