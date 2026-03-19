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
     gh issue list --state all --search "feat(<slug>-N)" --json number,title \
       | jq '.[0].number'
     ```

2. Read `.dev_cycle/project.md` to get the model for the review agent
   (look for the `review` row in the Models table; default: `claude-sonnet-4-6`).

3. Spawn a **foreground** review agent on the current branch (no new worktree):
   ```
   Agent tool:
     subagent_type: general-purpose
     run_in_background: false
     prompt: |
       Read .dev_cycle/agents/review_agent.md for your full instructions.
       Work order issue: #<N>
       Model: <model from project.md>
   ```

4. After the review agent runs and creates a PR, transition the issue label:
   ```bash
   gh issue edit <issue-N> --remove-label "dev-cycle:build" --add-label "dev-cycle:review"
   ```

   The PR body created by the review agent should include `Closes #<issue-N>` for
   GitHub auto-linking.

5. Show the agent's output to the user. If the verdict is `changes-needed`, the user
   can run `/fix` to address issues, then re-run `/review`.
