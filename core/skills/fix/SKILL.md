---
name: fix
description: >
  Fix bugs or make adjustments on an existing PR, or standalone bug fixes.
  Use when: "fix <PR#>", "fix this bug", "fix #23", or describing an issue to fix.
  Model: Sonnet — targeted fixes don't need full architecture reasoning.
---

# Fix Skill

## Invocation (main agent)

When this skill is invoked:

1. Parse the argument:
   - `/fix <PR#>` or `/fix #<PR#>` → **Mode A**: fix an existing PR's branch
   - `/fix <description>` → **Mode B**: standalone fix, creates its own branch + work order

2. Read `.dev_cycle/project.yaml` to get the model for the fix agent
   (look for the `fix` row in the Models table; default: `claude-sonnet-4-6`).

3. Spawn a **foreground** fix agent (no worktree — fixes happen on the existing branch):
   ```
   Agent tool:
     subagent_type: general-purpose
     run_in_background: false
     prompt: |
       Read `.dev_cycle/agents/fix/base.md` and `custom.md` (merged at runtime).
       Mode: A (PR fix) | B (standalone)
       PR number: <N>  [Mode A only]
       Description: <description>  [Mode B only]
       Model: <model from project.yaml>
   ```

4. The fix agent runs iteratively in this conversation. After it sets up context and
   the branch, forward subsequent user messages directly to it by resuming the agent.

5. When the user says "done" / "close" / "ship it", resume the agent with that signal
   so it can push and create/update the PR.

**Note:** After the initial `/fix` invocation, the user does NOT need to call `/fix`
again. Just describe the next issue — resume the same agent.
