---
name: deploy
description: >
  Start dev servers for a branch and monitor logs for errors.
  Use when: "deploy", "deploy <PR#>", "deploy #23", or "run this locally".
  Defaults to current branch if no PR specified.
  Model: Sonnet — mechanical task, no architecture reasoning needed.
---

# Deploy Skill

## Invocation (main agent)

When this skill is invoked:

1. Parse the argument:
   - `/deploy` → deploy current branch
   - `/deploy <PR#>` or `/deploy #<PR#>` → checkout that PR's branch and deploy

2. Read `.dev_cycle/project.md` to get the model for the deploy agent
   (look for the `deploy` row in the Models table; default: `claude-sonnet-4-6`).

3. Spawn a **foreground** deploy agent:
   ```
   Agent tool:
     subagent_type: general-purpose
     run_in_background: false
     prompt: |
       Read .dev_cycle/agents/deploy_agent.md for your full instructions.
       PR number: <N>  [if specified, else: "deploy current branch"]
       Model: <model from project.md>
   ```

4. The deploy agent runs continuously, monitoring logs and auto-fixing errors.
   Forward subsequent user messages to it by resuming the agent.

5. When the user says "stop" or "quit", resume the agent with that signal.

**Note:** The deploy agent reads `.dev_cycle/project.md` to learn the project's
server start commands, ports, and health check URLs. Make sure `project.md` is
configured before running `/deploy`.
