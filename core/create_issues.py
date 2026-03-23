#!/usr/bin/env python3
"""
Create GitHub issues from a taskmaster-format tasks.json file.

For each task (in order):
  1. Scan description/details for references to previously-processed taskIds.
  2. Replace those references with links to their GitHub issues.
  3. Create a GitHub issue with full details, labels, and phase metadata.
  4. Record the mapping  taskId -> (issue_number, issue_url).
  5. Prepend the task's description/details with the new issue number + link.
  6. Write the updated tasks.json back to disk.

Usage:
    python core/create_issues.py .taskmaster/tasks/tasks.json
    python core/create_issues.py tasks.json --dry-run
    python core/create_issues.py tasks.json --repo owner/repo
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def get_repo_info() -> tuple[str, str]:
    """Return (owner/repo, html_url) from the current git remote."""
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner,url"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data["nameWithOwner"], data["url"]


def ensure_labels_exist(labels: set[str], repo: str) -> None:
    """Create any labels that don't already exist in the repo."""
    result = subprocess.run(
        ["gh", "label", "list", "--repo", repo, "--json", "name", "--limit", "500"],
        capture_output=True,
        text=True,
    )
    existing: set[str] = set()
    if result.returncode == 0:
        existing = {l["name"] for l in json.loads(result.stdout)}

    for label in labels:
        if label not in existing:
            subprocess.run(
                ["gh", "label", "create", label, "--repo", repo, "--force"],
                capture_output=True,
                text=True,
            )
            existing.add(label)


def create_issue(
    title: str,
    body: str,
    labels: list[str],
    repo: str,
) -> tuple[int, str]:
    """Create a GitHub issue; return (issue_number, issue_url)."""
    cmd = [
        "gh", "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ]
    for label in labels:
        cmd.extend(["--label", label])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    url = result.stdout.strip()
    issue_number = int(url.rstrip("/").split("/")[-1])
    return issue_number, url


# ---------------------------------------------------------------------------
# Task field accessors (handles naming variations)
# ---------------------------------------------------------------------------

def _get(task: dict, *keys: str, default: object = "") -> object:
    for k in keys:
        if k in task:
            return task[k]
    return default


def get_task_id(task: dict) -> str:
    return str(_get(task, "taskId", "task_id", default=""))


def get_numeric_id(task: dict) -> int | None:
    val = _get(task, "id", default=None)
    return int(val) if val is not None else None


def get_title(task: dict) -> str:
    return str(_get(task, "title", default=get_task_id(task) or "Untitled"))


def get_description(task: dict) -> str:
    return str(_get(task, "description", default=""))


def get_details(task: dict) -> str:
    return str(_get(task, "details", default=""))


def get_phase(task: dict) -> str:
    return str(_get(task, "phase", "phaseName", "phase_name", default=""))


def get_tags(task: dict) -> list[str]:
    val = _get(task, "tags", "labels", default=[])
    return list(val) if isinstance(val, list) else []


def get_dependencies(task: dict) -> list[str]:
    deps = _get(task, "dependencies", default=[])
    if isinstance(deps, list):
        return [str(d) for d in deps]
    return []


def is_review_task(task: dict) -> bool:
    tid = get_task_id(task)
    return bool(tid and tid.upper().endswith("-R"))


# ---------------------------------------------------------------------------
# Cross-reference resolution
# ---------------------------------------------------------------------------

def replace_task_refs(
    text: str,
    mapping: dict[str, tuple[int, str]],
) -> str:
    """Replace bare taskId tokens with markdown links to their GitHub issues."""
    for task_id, (issue_number, issue_url) in mapping.items():
        # Match the taskId as a whole word, but not if it's already inside a
        # markdown link (preceded by '[' or followed by ']')
        pattern = rf"(?<!\[){re.escape(task_id)}(?!\])"
        replacement = f"[{task_id}]({issue_url})"
        text = re.sub(pattern, replacement, text)
    return text


# ---------------------------------------------------------------------------
# Issue body / label builders
# ---------------------------------------------------------------------------

def build_labels(task: dict) -> list[str]:
    labels: list[str] = []

    phase = get_phase(task)
    if phase:
        m = re.search(r"phase\s*(\d+)", phase, re.IGNORECASE)
        if m:
            labels.append(f"phase:{m.group(1)}")

    task_id = get_task_id(task)
    if task_id and not any(l.startswith("phase:") for l in labels):
        m = re.match(r"P(\d+)", task_id, re.IGNORECASE)
        if m:
            labels.append(f"phase:{m.group(1)}")

    labels.extend(get_tags(task))
    labels.append("dev-cycle:build")
    return list(dict.fromkeys(labels))  # dedupe, preserve order


def build_issue_body(
    task: dict,
    mapping: dict[str, tuple[int, str]],
) -> str:
    sections: list[str] = []

    phase = get_phase(task)
    task_id = get_task_id(task)
    if phase or task_id:
        header_parts = []
        if phase:
            header_parts.append(f"**Phase:** {phase}")
        if task_id:
            header_parts.append(f"**Task ID:** {task_id}")
        sections.append("  \n".join(header_parts))

    description = get_description(task)
    if description:
        sections.append(f"## Description\n\n{description}")

    details = get_details(task)
    if details:
        sections.append(f"## Technical Brief\n\n{details}")

    design_ref = str(_get(task, "designReference", "design_reference", default=""))
    if design_ref:
        sections.append(f"## Design Reference\n\n{design_ref}")

    criteria = str(_get(task, "acceptanceCriteria", "acceptance_criteria", default=""))
    if criteria:
        sections.append(f"## Acceptance Criteria\n\n{criteria}")

    deps = get_dependencies(task)
    if deps:
        lines: list[str] = []
        for dep in deps:
            if dep in mapping:
                num, url = mapping[dep]
                lines.append(f"- [{dep}]({url}) (#{num})")
            else:
                lines.append(f"- {dep}")
        sections.append("## Dependencies\n\n" + "\n".join(lines))

    body = "\n\n".join(sections)
    body = replace_task_refs(body, mapping)
    return body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from a taskmaster-format tasks.json",
    )
    parser.add_argument("tasks_file", help="Path to tasks.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without hitting GitHub",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo (owner/repo). Auto-detected from git remote if omitted.",
    )
    args = parser.parse_args()

    tasks_path = Path(args.tasks_file)
    if not tasks_path.exists():
        sys.exit(f"File not found: {tasks_path}")

    with open(tasks_path) as f:
        data = json.load(f)

    # tasks.json may be a bare list or {"tasks": [...]}
    if isinstance(data, list):
        tasks: list[dict] = data
    else:
        tasks = data.get("tasks", [])

    if args.repo:
        repo = args.repo
        repo_url = f"https://github.com/{repo}"
    else:
        repo, repo_url = get_repo_info()

    print(f"Repository : {repo}")
    print(f"Tasks file : {tasks_path}")
    print(f"Total tasks: {len(tasks)}")
    if args.dry_run:
        print("Mode       : DRY RUN (no issues will be created)\n")
    else:
        print()

    # Pre-create all labels we'll need
    all_labels: set[str] = set()
    for task in tasks:
        if not is_review_task(task):
            all_labels.update(build_labels(task))
    if not args.dry_run and all_labels:
        print(f"Ensuring labels exist: {', '.join(sorted(all_labels))}")
        ensure_labels_exist(all_labels, repo)
        print()

    # taskId (and stringified numeric id) -> (issue_number, issue_url)
    mapping: dict[str, tuple[int, str]] = {}

    for idx, task in enumerate(tasks, 1):
        task_id = get_task_id(task)
        numeric_id = get_numeric_id(task)
        title = get_title(task)

        if is_review_task(task):
            print(f"[{idx}/{len(tasks)}] SKIP review task {task_id}")
            continue

        display_id = task_id or str(numeric_id)
        print(f"[{idx}/{len(tasks)}] {display_id}: {title}")

        body = build_issue_body(task, mapping)
        labels = build_labels(task)

        if args.dry_run:
            print(f"  Labels : {labels}")
            print(f"  Body   : {body[:120].replace(chr(10), ' ')}…")
            fake_num = 1000 + idx
            fake_url = f"{repo_url}/issues/{fake_num}"
            if task_id:
                mapping[task_id] = (fake_num, fake_url)
            if numeric_id is not None:
                mapping[str(numeric_id)] = (fake_num, fake_url)
            print()
            continue

        # --- actually create the issue ---
        issue_number, issue_url = create_issue(title, body, labels, repo)
        print(f"  -> #{issue_number}  {issue_url}")

        # record mapping
        if task_id:
            mapping[task_id] = (issue_number, issue_url)
        if numeric_id is not None:
            mapping[str(numeric_id)] = (issue_number, issue_url)

        # prepend issue header to description
        issue_header = f"Your issue number is #{issue_number} — {issue_url}"
        desc = get_description(task)
        task["description"] = f"{issue_header}\n\n{desc}" if desc else issue_header

        details = get_details(task)
        if details:
            task["details"] = f"> {issue_header}\n\n{details}"

        # update metadata
        task.setdefault("metadata", {})
        task["metadata"]["githubIssue"] = issue_number
        task["metadata"]["githubIssueUrl"] = issue_url

    # Write the updated tasks.json back
    if not args.dry_run:
        if isinstance(data, list):
            output_data = tasks
        else:
            data["tasks"] = tasks
            output_data = data

        with open(tasks_path, "w") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\n✓ Updated {tasks_path} with issue numbers and metadata.")

    # Summary
    print("\n=== Task → Issue Mapping ===")
    seen: set[int] = set()
    for tid, (num, url) in mapping.items():
        if num not in seen:
            print(f"  {tid:>10}  →  #{num}  {url}")
            seen.add(num)

    print(f"\nTotal issues created: {len(seen)}")


if __name__ == "__main__":
    main()
