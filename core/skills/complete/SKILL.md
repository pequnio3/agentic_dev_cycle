---
name: complete
description: >
  Close a merged work order's GitHub Issue and capture learnings.
  Use when: "complete <slug>-N", "complete pr-N", or after merging a PR.
---

# Complete Work Order

Close the GitHub Issue for a work order after its PR has been merged,
and capture key decisions as GitHub Issues labeled `dev-cycle:decision`.

## Step 1: Resolve the Issue Number

**If argument is `<slug>-N`** (e.g. `gemini-provider-1`):
```bash
gh issue list --state all --search "in:title <slug>-N:" --json number,title \
  | jq '.[0].number'
```

**If argument is `pr-N`** (e.g. `pr-6`):
```bash
gh pr view 6 --json closingIssuesReferences \
  --jq '.closingIssuesReferences[].number'
```
If the PR body doesn't auto-link, check the PR title for a `<slug>-N:` pattern
and search for the matching issue.

## Step 2: Verify PR is Merged (HARD GATE)

```bash
gh pr view <PR#> --json state,mergedAt --jq '{state: .state, mergedAt: .mergedAt}'
```

If `state != "MERGED"` — **STOP**. Do not complete an unmerged work order. Tell the user:
> "PR #N is not yet merged. Please merge it first, then re-run `/complete`."

## Step 3: Close the Issue

```bash
gh issue edit <issue-N> --remove-label "dev-cycle:review" --add-label "dev-cycle:done"
gh issue close <issue-N> --comment "Merged via PR #<PR>. Marking complete."
```

## Step 4: Write Decision Issue

Read the issue body's Implementation Notes:
```bash
gh issue view <issue-N> --json body --jq '.body'
```

Extract anything worth preserving for future agents:
- Architectural choices made during implementation
- Gotchas that would surprise a future agent
- Things to avoid (anti-patterns discovered)

If there is nothing worth preserving, skip this step.

If there is, ensure the `dev-cycle:decision` label exists:
```bash
gh label create "dev-cycle:decision" --color "d93f0b" --description "Architectural decision or gotcha for future agents" 2>/dev/null || true
```

Create one decision issue per distinct topic (don't bundle unrelated decisions):
```bash
gh issue create \
  --title "decision(<slug>-N): <topic in 5-8 words>" \
  --label "dev-cycle:decision" \
  --body "$(cat <<'EOF'
**Feature:** <slug>-N (PR #<PR>)
**Files touched:** <comma-separated list of key files>

**Decision:** <what was decided and why — 2-4 sentences>
**Gotcha:** <what would surprise a future agent — be specific>
**Avoid:** <explicit anti-pattern — "do not X because Y">
EOF
)"
```

**Self-contained rule:** Each decision issue must be fully understandable on its own.
Do NOT reference other decision issues as prerequisites. If prior context is needed to
understand this decision, summarize it inline. A build agent reads this issue in isolation
and must get full value from it alone.

## Step 5: Report

- Issue #N closed and labeled `dev-cycle:done`
- Decision issue(s) created: #N1, #N2 (or "none — no decisions worth preserving")
