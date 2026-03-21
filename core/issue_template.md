<!-- GitHub issue title: `<slug>-N: <short description>` (same pattern for PR titles) -->

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

## Agent focus (optional)

<!-- Per-issue emphasis when this work order needs a one-off stance. Omit to rely on `.dev_cycle/agents/build/custom.md` and repo defaults. -->

## Correctness validation

<!-- Filled in by the build agent before marking this work order complete: concrete, verifiable steps tied to the Idea and Scenarios. Replace comments; check boxes when done. -->

### Automated checks

- [ ] **Iteration / pre-PR gates:** <!-- e.g. `./.dev_cycle/gates.sh iteration` then `pre-pr` — paste key output or “clean” -->
- [ ] **Targeted tests:** <!-- commands + what “green” means for this change -->

### Manual / scenario checks

- [ ] <!-- Numbered step: action → expected result (map to Scenarios above) -->
- [ ] <!-- Add one row per critical scenario or edge case -->

### Evidence

<!-- Short notes or pasted output proving the checks above passed. -->

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
