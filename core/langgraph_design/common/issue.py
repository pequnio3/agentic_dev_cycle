"""GitHub Issue body template for dev-cycle work orders (matches `core/issue_template.md` structure)."""

from __future__ import annotations

from common.types import PhaseSpec

# Kept in sync with `core/issue_template.md` (design / queue skills). Format with
# `generate_issue_body(...)`.
ISSUE_BODY_TEMPLATE = """<!-- GitHub issue title: `{slug}-{n}: <short description>` (same pattern for PR titles) -->

Slug: {slug}-{n}
Branch: dev-{slug}-{n}
PR: —
Created: {today}
Design: {design_doc_path}
Depends on: {depends}
Parallel safe: {parallel}

## Idea

{idea}

## Context Manifest

{context_manifest}
**Complexity:** simple | medium | large
**Relevant decisions:** #N, #N  ← omit line if none
{scenarios_section}## Plan

<!-- Filled in by build agent -->

## Agent focus (optional)

<!-- Per-issue emphasis (e.g. performance, security, UX) when this work order needs a one-off stance. Omit to rely on `.dev_cycle/agents/build/custom.md` and repo defaults. -->

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

- **Branch:** dev-{slug}-{n}
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
"""


def _scenarios_block(phase: PhaseSpec) -> str:
    scen = phase["scenarios_markdown"]
    if scen.strip():
        return f"\n## Scenarios\n\n{scen}\n"
    return "\n## Scenarios\n\n_Not applicable — no behavioral contract to specify._\n"


def generate_issue_body(
    *,
    slug: str,
    n: int,
    depends: str,
    parallel: str,
    phase: PhaseSpec,
    today: str,
    design_doc_path: str | None = None,
) -> str:
    """
    Build the full GitHub Issue body for one work order.

    `design_doc_path` defaults to `.dev_cycle/design/<slug>.md` (runtime path after install).
    """
    path = design_doc_path if design_doc_path is not None else f".dev_cycle/design/{slug}.md"
    idea = phase["idea_markdown"]
    ctx = phase["context_manifest_markdown"] or "<!-- scoped from design doc -->"
    scenarios_section = _scenarios_block(phase)
    return ISSUE_BODY_TEMPLATE.format(
        slug=slug,
        n=n,
        today=today,
        design_doc_path=path,
        depends=depends,
        parallel=parallel,
        idea=idea,
        context_manifest=ctx,
        scenarios_section=scenarios_section,
    )
