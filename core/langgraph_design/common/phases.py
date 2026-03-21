from __future__ import annotations

import re

from common.types import PhaseSpec


def parse_phased_implementation(design_markdown: str) -> list[PhaseSpec]:
    """
    Split the design doc into work-order phases.

    If a `## Phased Implementation` section exists, each `###` subsection becomes
    one phase. Otherwise returns a single phase using the full doc as Idea (minus
    obvious boilerplate).
    """
    text = design_markdown
    m = re.search(
        r"^##\s+Phased Implementation\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return [_single_phase(text)]

    after = text[m.end() :]
    stop = re.search(r"^##\s+", after, re.MULTILINE)
    section = after[: stop.start()] if stop else after

    chunks = re.split(r"^###\s+", section, flags=re.MULTILINE)
    phases: list[PhaseSpec] = []
    if chunks[0].strip():
        phases.append(_phase_from_block("Phase 1", chunks[0].strip()))
    for raw in chunks[1:]:
        raw = raw.strip()
        if not raw:
            continue
        first_line, _, body = raw.partition("\n")
        title = first_line.strip() or "Phase"
        phases.append(_phase_from_block(title, body.strip()))

    if not phases:
        return [_single_phase(text)]
    return phases


def _single_phase(full: str) -> PhaseSpec:
    """One work order for designs without phased section."""
    idea = _extract_section(full, "Proposed Solution") or _extract_section(
        full, "The Problem"
    )
    if not idea:
        idea = full[:8000]
    ctx = _extract_section(full, "Context Manifest") or ""
    scen = _extract_section(full, "Scenarios") or ""
    return {
        "short_title": "implementation",
        "idea_markdown": idea.strip() or full[:4000],
        "context_manifest_markdown": ctx.strip(),
        "scenarios_markdown": scen.strip(),
    }


def _phase_from_block(title: str, body: str) -> PhaseSpec:
    idea = _extract_section(body, "Idea") or body
    ctx = _extract_section(body, "Context Manifest") or ""
    scen = _extract_section(body, "Scenarios") or ""
    short = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    short = re.sub(r"\s+", "-", short)[:48] or "phase"
    return {
        "short_title": short,
        "idea_markdown": idea.strip(),
        "context_manifest_markdown": ctx.strip(),
        "scenarios_markdown": scen.strip(),
    }


def _extract_section(md: str, name: str) -> str | None:
    pattern = rf"^##\s+{re.escape(name)}\s*$(.*?)(?=^##\s+|\Z)"
    m = re.search(pattern, md, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None
