# <Title>

Slug: <slug>-N
Branch: dev-<slug>-N
PR: —
Created: YYYY-MM-DD
Design: .dev_cycle/design/<slug>.md
Depends on: none
Parallel safe: yes

## Idea

<What to build — paste the relevant phase content from the design doc>

## Context Manifest

<Files the build agent should read — copy from design doc, scoped to this phase>
**Complexity:** simple | medium | large
**Relevant decisions:** #N, #N  ← omit line if none

## Scenarios

<BDD scenarios scoped to this phase — omit this section entirely if none>

## Plan

<!-- Filled in by build agent -->

## Implementation Notes

- **Branch:** dev-<slug>-N
- **Commits:**
- **Deviations from plan:**
- **Scenarios passing:** <!-- N / N, or N/A -->

## Review

- [ ] Code correctness
- [ ] No spec drift — every Idea requirement implemented
- [ ] Scenarios pass — all BDD scenarios green (if present)
- [ ] No regressions
- [ ] Gate checks pass (`./.dev_cycle/gates.sh pre-pr`)

**Review verdict:** pending
