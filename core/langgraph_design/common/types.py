"""Shared TypedDicts used by multiple skill graphs (design, queue, future build, …)."""

from __future__ import annotations

from typing import TypedDict


class PhaseSpec(TypedDict):
    """One queued work order derived from a design doc."""

    short_title: str
    idea_markdown: str
    context_manifest_markdown: str
    scenarios_markdown: str
