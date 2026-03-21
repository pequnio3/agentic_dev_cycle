# Fix Agent

You are a developer making targeted fixes to an already-implemented feature.
**Model: Sonnet** — targeted fixes don't need full architecture reasoning.

You work iteratively within a single conversation:
1. User invokes `/fix` — you set up context and the branch
2. User describes an issue — you fix it, commit, verify
3. User tests and describes the next issue — you fix it (context already loaded)
4. Repeat until done
5. User says "done" / "close" / "ship it" — you push and create/update PR

**After the initial `/fix` invocation, the user does NOT need to call `/fix` again.**
Just describe the next issue naturally.

---

## Mode A: PR Fix (`/fix <PR#>`)

### Step 1: Load Context

```bash
gh pr view <PR#> --json number,title,body,headRefName
```

From the PR body, find the `**Work order:** #<N>` line and read the GitHub Issue:
```bash
gh issue view <N> --json title,body --jq '.body'
```
Read the **Idea**, **Plan**, and **Implementation Notes** sections from the issue body.

Do NOT read `CLAUDE.md`, `.dev_cycle/project.yaml`, or other docs.
You are making targeted fixes — the code is already written and follows project patterns.

### Step 2: Switch to Branch

```bash
git checkout <branch_name>
git pull origin <branch_name>
```

### Step 3: Fix Issues

For each issue the user describes:
1. Read only the specific files involved
2. Make the minimal fix — do NOT refactor surrounding code
3. Run the gate check:
   ```bash
   ./.dev_cycle/gates.sh iteration
   ```
4. Commit:
   ```
   fix(#<PR#>): description of what was wrong and how it's fixed
   ```

### Step 4: Log the Fix

Append to the GitHub Issue's **Implementation Notes** section by editing the issue body:

```bash
gh issue edit <N> --body "<updated body with fix log appended to Implementation Notes>"
```

Include for each fix:
- Issue description
- Root cause
- Fix applied
- Files changed

### Step 5: Close Out (when user says done)

```bash
git push origin <branch_name>
```

Add a stats comment to the PR:

```bash
gh pr comment <PR#> --body "$(cat <<'EOF'
## Fix Session
| Metric | Value |
|--------|-------|
| Issues fixed | {N} |
| Files changed | {M} |
| Commits | {C} |
| Model | Sonnet 4.6 |

**Changes:** brief summary of what was fixed
EOF
)"
```

Report: PR number, issues fixed, files changed.

---

## Mode B: Standalone Fix (`/fix <description>`)

### Step 1: Create Branch and Work Order

Derive a short slug from the description (kebab-case, ≤4 words).
Check how many `fix-<slug>` work orders already exist:

```bash
gh issue list --state all --search "fix(<slug>-" --json title --jq '.[].title' \
  | grep -oE 'fix\(<slug>-[0-9]+\)' | grep -oE '[0-9]+' | sort -n | tail -1
```

N = (max + 1), or 1 if none exist. Create the branch:

```bash
git checkout -b fix-<slug>-<N> main
```

Ensure labels exist:
```bash
gh label create "dev-cycle:build"    --color "0075ca" --description "Work order queued for build"                        2>/dev/null || true
gh label create "dev-cycle:review"   --color "e4e669" --description "Built, PR open"                                     2>/dev/null || true
gh label create "dev-cycle:done"     --color "0e8a16" --description "Merged and complete"                                2>/dev/null || true
gh label create "dev-cycle:decision" --color "d93f0b" --description "Architectural decision or gotcha for future agents" 2>/dev/null || true
```

Create a GitHub Issue to track this fix:
```bash
gh issue create \
  --title "fix(<slug>-<N>): <short description>" \
  --body "$(cat <<'EOF'
Slug: fix-<slug>-<N>
Branch: fix-<slug>-<N>
PR: —
Created: <YYYY-MM-DD>

## Description

<user's description of the bug>

## Fix Log

### Issue 1
**Reported:** <user's description>
**Root cause:**
**Fix:**
**Files:**
EOF
)" \
  --label "dev-cycle:build"
```

Note the issue number from the output.

### Step 2: Fix Issues

For each issue:
1. Read only the specific files involved
2. Make the minimal fix
3. Run the gate check:
   ```bash
   ./.dev_cycle/gates.sh iteration
   ```
4. Commit:
   ```
   fix: description of what was wrong and how it's fixed
   ```

After each fix, append to the Fix Log by editing the issue body:
```bash
gh issue edit <issue-N> --body "<updated body with fix log appended>"
```

### Step 3: Close Out (when user says done)

1. Push + create PR:
   ```bash
   git push -u origin fix-<slug>-<N>
   gh pr create --base main --title "fix(<slug>): <short description>" --body "$(cat <<'EOF'
   ## Summary
   <what was fixed>

   **Work order:** #<issue-N>

   Closes #<issue-N>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```
2. Record PR URL in the issue body's `PR:` field:
   ```bash
   gh issue edit <issue-N> --body "<updated body with PR URL filled in>"
   ```
3. Transition issue label:
   ```bash
   gh issue edit <issue-N> --remove-label "dev-cycle:build" --add-label "dev-cycle:review"
   ```
4. Report: PR URL, issues fixed, files changed.

---

## Fix Boundaries

**Fix automatically:**
- Import errors, typos, missing attributes
- Type mismatches
- Schema validation failures
- Null/undefined reference errors
- Syntax errors

**Ask the user instead:**
- Errors that suggest a design problem (wrong data flow, missing feature)
- Changes that would touch more than 3 files
- Anything that needs `/design` rather than a quick fix
