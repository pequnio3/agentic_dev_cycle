Role: Act as a Senior Technical Project Manager and Systems Architect.
Task: Analyze the attached design document. Break down the transition from the [Existing System] to the [New System] into a granular, execution-ready task list.

Requirements:

Phased Structure: Organize tasks strictly according to the phases defined in the document.
Granularity: Each task must be a single, "testable" unit of work that can be completed independently (e.g., "Create API endpoint for X" rather than "Build backend").
Contextual Continuity: For each task, briefly note if it replaces an existing component or adds a new one to ensure no logic is lost during the migration.
Sequential Order: List tasks in the exact order they must be executed within each phase, noting any hard dependencies (e.g., "Task B requires Task A").

## Input

The design dic provided contains:

- Full product requirements and work item breakdown
- Potential Figma/image design references (file URL, frame-to-work-item mapping, image filenames)
- Suggested execution order and phase definitions

Read the design document fully before generating tasks.

## Figma Design References

The design document MAY include a **Figma Frame Reference** section that maps each screen to:

- A local screenshot in the `images/` subdirectory (if exported)
- A Figma deep-link URL for interactive inspection
- The Figma `nodeId` for use with MCP tools

For each **UI task**, the generated task MUST include a **"Design Reference"** section that:

1. Embeds the relevant frame screenshots using GitHub-compatible Markdown image syntax. Use raw GitHub URLs so images render in the issue body:
   ```
   ![Camera — idle](../blob/<branch>/<pathath/to/image.png)
   ```   
2. Includes the Figma deep-link URL so the developer can inspect the design interactively.
3. Calls out specific visual details the developer should match:
   - Color values and gradients
   - Icon placement, size, and style
   - Spacing, padding, border radius
   - Typography (font size, weight, color)
   - Component states (enabled/disabled, active/inactive, pressed)
4. Notes the Figma `nodeId` so the developer can call `get_design_context` or `get_screenshot` via the Figma MCP for additional detail at build time.

For **non-UI tasks** (data layer, provider refactor, code removal, cleanup), skip the Design Reference section.

## Branching Strategy

**Phase = branch, Task = commit.**

Each phase gets its own Git branch. Tasks within a phase are individual commits on that branch — not separate branches. This avoids cascading rebase problems across tightly coupled work items while preserving granular history.

Branch naming: `<major_feature>/phase-<N>-<phase-slug>`

Where `<major_feature>` is a short slug representing the original design doc.

### Phase branches

| Branch | Merges into | Gate |
|---|---|---|
| `<major_feature>/phase-0-<slug>` | `main` | Can run in parallel with Phase 1 if independent |
| `<major_feature>/phase-1-<slug>` | `main` | Merges after Phase 0 (or in parallel if independent) |
| `<major_feature>/phase-2-<slug>` | `main` | Branches from `main` after Phase 1 merges |
| `<major_feature>/phase-3-<slug>` | `main` | Branches from `main` after Phase 2 merges |

### Commit convention

Each task within a phase is a single commit (or small series of commits) on the phase branch. Commit messages reference the GitHub Issue:

```
<task_id>: <actionable title> (closes #<issue_number>)

<brief description of what changed and why>
```

The `closes #N` keyword auto-closes the issue when the phase branch merges to `main`.

### Why not branch-per-task

- Tasks within a phase are tightly coupled and often touch the same files.
- A dependency chain of 10+ branches creates cascading rebase overhead.
- Commits provide the same granularity: `git log`, `git bisect`, `git revert <commit>`.
- Review happens at the phase/PR level, which is more meaningful than micro-PRs.

## Tasks Branch ##
The tasks.json file should be in the following format
```json
{
  "<feature_slug>": {
    "tasks": [
      {
        "id": "<task_id>",
        "title": "<title>",
        "description": "<description>",
        "details": "<details>",
        "status": "pending",
        "dependencies": [],
        "priority": "<priority>",
        "subtasks": [],
        "tags": [],
        "metadata": {}
      }
    ]
  }
}
```
Each task description has these fields. They appear in both the GitHub Issue body AND the `tasks.json` entry:

- **Task ID** (e.g., P1-01)
- **Phase Name**
- **Actionable Title**
- **Technical Brief** (detailed description of the task and any relevant information)
- **Design Reference** (for UI tasks — embedded frame screenshots + visual specs; see Figma section above)
- **Acceptance Criteria** (what "done" looks like)
- **Dependencies** (other task IDs that must be complete first)


### Phase review task

The **last task in each phase** is a review task. It is NOT a GitHub Issue — it is only a `tasks.json` entry so taskmaster can delegate it to a reviewer agent.

Task ID convention: `P<N>-R` (e.g., `P1-R`, `P2-R`)

The review task depends on all other tasks in the phase being complete. Its job:

1. Open a PR from the phase branch to `main`. The PR description lists all issues the phase closes (`Closes #45, #46, #47`).
2. Review every commit on the phase branch against the acceptance criteria in each corresponding issue.
3. For UI tasks, compare the implementation against the Figma frame screenshots embedded in the issue bodies. Flag visual deviations (wrong colors, spacing, icon placement, missing states).
4. Run project gate checks (lint, analyze, tests) on the branch.
5. If fixes are needed, commit them directly to the phase branch (not as issue-closing commits — these are fix-up commits).
6. Once the PR passes review, mark the review task complete.

The review task's `details` in `tasks.json` should list:
- All task IDs and issue numbers in the phase
- The phase branch name
- A checklist of what to verify (acceptance criteria from each issue, plus visual checks for UI tasks, plus gate commands)

### Worker acceptance criteria

Individual tasks use the acceptance criteria checkboxes on the GitHub Issue. The worker checks these off as it completes each item. This gives immediate per-task status without waiting for the review.

## Output: tasks.json

Add each task to `.taskmaster/tasks/tasks.json` in its workree in the taskmaster-ai format. The `details` field MUST contain the **full task spec** (same content as the GitHub Issue body) so that taskmaster can delegate to a worker agent without needing to fetch the issue from GitHub. The tasks github issue, and previous issues in its phases will be added post task generation by a human.

The tasks.json is the **agent's working memory** — it must be self-contained. The GitHub Issue is the **durable human record** — it must be linkable from commits and PRs.

### Task types in tasks.json

| Type | Has GitHub Issue? | Has `details`? | Role |
|---|---|---|---|
| Build task | Yes | Yes (full spec) | Worker implements and commits |
| Review task (`P<N>-R`) | No | Yes (checklist + task IDS) | Reviewer opens PR, reviews, fixes |

For developer descriptions add the following instructions (you should fill in <> points )

1. <Provide git related instructions specifying actual branches>
2. Implement the task task below. 
3. Commit with: `<task_id>: <title> (closes #task_issue_number)`
4. Move to the next task in the phase.

## Reviewer Agent Instructions (top of Description)
1. <Provide git related instructions specifying actual branches> (Open a PR from the phase branch to `main`, listing all closed issues in the body.)
2. Walk through every commit on the branch, checking each against its issue's acceptance criteria.
3. For UI tasks, compare the rendered app against any refrenced screenshots in the issue body.
4. Run gate checks relevant to the codebase.
5. Commit fixes directly to the phase branch if needed.
6. Close All the associated issues.
7. Mark the review task complete once the PR is ready for merge.