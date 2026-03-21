---
name: deploy
description: >
  Start dev servers for a branch and monitor logs for errors.
  Use when: "deploy", "deploy #23", "deploy 23", "deploy model-picker-1", "deploy dev-foo-2",
  or "run this locally". Defaults to current branch if no argument.
  Model: Sonnet — mechanical task, no architecture reasoning needed.
---

# Deploy Skill

## Invocation (main agent)

When this skill is invoked:

1. Parse the argument (first token after `/deploy`, if any):

   | Input | Meaning |
   |-------|---------|
   | *(none)* | Stay on **current branch** |
   | `#<N>` or `<N>` where the whole token is digits | **PR number** `<N>` — resolve head branch via `gh pr view` |
   | starts with `dev-` | Use as **full branch name** literally |
   | anything else (e.g. `model-picker-1`, `dark-mode`) | **Work-order slug** — checkout **`dev-<token>`** (matches `Branch: dev-<slug>-<N>` on issues) |

   **Ambiguity:** A token that is **only digits** is treated as a PR number, not a slug.

2. Read `.dev_cycle/project.yaml` to get the model for the deploy agent
   (look for the `deploy` row in the Models table; default: `claude-sonnet-4-6`).

3. Spawn a **foreground** deploy agent. Put **exactly one** of these lines in the prompt
   (omit the others):

   ```
   Agent tool:
     subagent_type: general-purpose
     run_in_background: false
     prompt: |
       Read `.dev_cycle/agents/deploy/base.md` and `custom.md` (merged at runtime).
       Deploy mode: pr | branch | current
       PR number: <N>                    ← only if mode is pr
       Feature branch: dev-<slug>-<N>  ← only if mode is branch
       Model: <model from project.yaml>
   ```

   For **current branch**: `Deploy mode: current` and omit PR / Feature branch lines.

4. The deploy agent runs continuously, monitoring logs and auto-fixing errors.
   Forward subsequent user messages to it by resuming the agent.

5. When the user says "stop" or "quit", resume the agent with that signal.

**Note:** The deploy agent reads `.dev_cycle/project.yaml` to learn the project's
server start commands, ports, and health check URLs. Make sure `project.yaml` is
configured before running `/deploy`.
