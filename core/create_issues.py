#!/usr/bin/env python3
"""
Create GitHub issues from a taskmaster-format tasks.json file.

For each task (in order):
  1. Scan description/details for references to previously-processed taskIds.
  2. Replace those references with links to their GitHub issues.
  3. Create a GitHub issue (or reuse if metadata.githubIssue exists, or an issue with the same title exists).
  4. Record the mapping  taskId -> (issue_number, issue_url).
  5. Prepend the task's description/details with the new issue number + link (new issues only).
  6. Write the updated tasks.json back to disk.

Usage:
    python core/create_issues.py .taskmaster/tasks/tasks.json
    python .dev-cycle/core/create_issues.py .taskmaster/tasks/tasks.json --tag <slug>   # after install.sh
    python core/create_issues.py tasks.json --dry-run
    python core/create_issues.py tasks.json --repo owner/repo
    python core/create_issues.py tasks.json --tag v2

Repo detection: unless --repo is set, the GitHub repo is taken from the git
repository that contains tasks.json (not the shell's current directory).

"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def git_repo_root_containing(path: Path) -> Path | None:
    """Return the git work tree root that contains `path`, or None if not in a repo."""
    resolved = path.resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    if not start.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())



def get_repo_info(cwd: Path | None = None) -> tuple[str, str]:
    """Return (owner/repo, html_url) via gh for the repo at cwd (default: process cwd)."""
    run_kw: dict[str, object] = {
        "capture_output": True,
        "text": True,
        "check": True,
    }
    if cwd is not None:
        run_kw["cwd"] = str(cwd)
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner,url"],
        **run_kw,
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
    """Create a GitHub issue; return (issue_number, issue_url).

    Body is written to a temp file and passed with ``gh issue create --body-file``
    to avoid OS argv length limits on huge descriptions.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as f:
        f.write(body)
        body_path = f.name

    try:
        cmd = [
            "gh", "issue", "create",
            "--repo", repo,
            "--title", title,
            "--body-file", body_path,
        ]
        for label in labels:
            cmd.extend(["--label", label])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            msg = f"gh issue create failed (exit {result.returncode})"
            if err:
                msg += f":\n{err}"
            sys.exit(msg)
        url = result.stdout.strip()
        issue_number = int(url.rstrip("/").split("/")[-1])
        return issue_number, url
    finally:
        Path(body_path).unlink(missing_ok=True)


def parse_stored_github_issue_metadata(task: dict, repo_url: str) -> tuple[int, str] | None:
    """Return (issue_number, issue_url) from task metadata if present."""
    meta = task.get("metadata")
    if not isinstance(meta, dict):
        return None
    raw = meta.get("githubIssue")
    if raw is None:
        return None
    try:
        num = int(raw)
    except (TypeError, ValueError):
        return None
    if num < 1:
        return None
    url = meta.get("githubIssueUrl")
    if isinstance(url, str) and url.strip():
        return num, url.strip()
    base = repo_url.rstrip("/")
    return num, f"{base}/issues/{num}"


def fetch_github_issue_url(repo: str, issue_number: int) -> str | None:
    """Return the issue's canonical HTML URL if it exists on GitHub, else None."""
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "url"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        url = json.loads(result.stdout).get("url")
    except json.JSONDecodeError:
        return None
    return url if isinstance(url, str) and url.strip() else None


def find_issue_by_exact_title(repo: str, title: str) -> tuple[int, str] | None:
    """If any issue in the repo has exactly this title (open or closed), return (number, url)."""
    for state in ("open", "closed"):
        result = subprocess.run(
            [
                "gh",
                "search",
                "issues",
                title,
                "--repo",
                repo,
                "--match",
                "title",
                "--state",
                state,
                "--json",
                "number,title,url",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            continue
        try:
            items = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        for item in items:
            if item.get("title") == title:
                num = item.get("number")
                url = item.get("url")
                if isinstance(num, int) and isinstance(url, str):
                    return num, url
    return None


def apply_issue_to_task(
    task: dict,
    issue_number: int,
    issue_url: str,
    *,
    update_prose: bool,
) -> None:
    """Store metadata; optionally prepend issue header to description/details (new issues only)."""
    if update_prose:
        issue_header = f"Your issue number is #{issue_number} — {issue_url}"
        desc = get_description(task)
        task["description"] = f"{issue_header}\n\n{desc}" if desc else issue_header
        details = get_details(task)
        if details:
            task["details"] = f"> {issue_header}\n\n{details}"
    task.setdefault("metadata", {})
    task["metadata"]["githubIssue"] = issue_number
    task["metadata"]["githubIssueUrl"] = issue_url


# ---------------------------------------------------------------------------
# Task field accessors (handles naming variations)
# ---------------------------------------------------------------------------

def _get(task: dict, *keys: str, default: object = "") -> object:
    for k in keys:
        if k in task:
            return task[k]
    return default


def get_task_id(task: dict) -> str:
    # Prefer explicit taskId; fall back to `id` (taskmaster-ai often uses id for P1-01-style ids).
    return str(_get(task, "taskId", "task_id", "id", default=""))


def get_numeric_id(task: dict) -> int | None:
    """Numeric task id for mapping, if present (subtasks / internal ids). Skip string task ids."""
    val = _get(task, "id", default=None)
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)
    return None


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
    """Replace bare taskId tokens with markdown links to their GitHub issues.

    Purely numeric ids (e.g. internal task row numbers) are *not* linkified: they
    match digits inside GitHub URLs, issue numbers, branch names, and hostnames.
    """
    safe = [(tid, pair) for tid, pair in mapping.items() if tid and not tid.isdigit()]
    # Longer ids first so P2-01 is not partially consumed if P2 also exists.
    safe.sort(key=lambda x: len(x[0]), reverse=True)
    for task_id, (_issue_number, issue_url) in safe:
        # Match the taskId as a whole word, but not if it's already inside a
        # markdown link (preceded by '[' or followed by ']')
        pattern = rf"(?<!\[){re.escape(task_id)}(?!\])"
        replacement = f"[{task_id}]({issue_url})"
        text = re.sub(pattern, replacement, text)
    return text


# ---------------------------------------------------------------------------
# Issue body / label builders
# ---------------------------------------------------------------------------

def build_labels(task: dict, feature_slug: str) -> list[str]:
    """Build GitHub labels: phase + feature slug + dev-cycle. Task `tags` are not applied."""
    labels: list[str] = []

    if feature_slug.strip():
        labels.append(feature_slug.strip())

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
    parser.add_argument(
        "--tag",
        default="master",
        help=(
            "Which task set to use: key under {\"tasks\": {...}} or a top-level feature slug "
            "(e.g. tiktok-capture). Default: master — if your tasks live under another key, "
            "pass it explicitly or you will load the wrong slice or none."
        ),
    )
    args = parser.parse_args()

    tasks_path = Path(args.tasks_file)
    if not tasks_path.exists():
        sys.exit(f"File not found: {tasks_path}")

    with open(tasks_path) as f:
        data = json.load(f)

    tag = args.tag
    tasks: list[dict] = []
    # True when tasks live at data[tag]["tasks"] (taskmaster-ai / feature-slug shape).
    tag_nested_tasks: bool = False

    if isinstance(data, list):
        tasks = data
    elif isinstance(data.get("tasks"), dict):
        # {"tasks": {"master": [...], "v2": [...]}}
        if tag not in data["tasks"]:
            sys.exit(f"Tag '{tag}' not found in tasks. Available: {', '.join(data['tasks'].keys())}")
        tasks = data["tasks"][tag]
    elif tag in data:
        # {"tiktok-capture": {"tasks": [...]}} or {"v2": [...]}
        node = data[tag]
        if isinstance(node, dict) and isinstance(node.get("tasks"), list):
            tasks = node["tasks"]
            tag_nested_tasks = True
        elif isinstance(node, list):
            tasks = node
        else:
            sys.exit(
                f"Under tag '{tag}', expected a list of tasks or an object with a "
                f'"tasks" array, got: {type(node).__name__}'
            )
    else:
        # {"tasks": [...]} (flat list, tag ignored)
        tasks = data.get("tasks", [])

    if not tasks and isinstance(data, dict):
        slug_keys = [
            k
            for k in data
            if isinstance(data[k], dict) and isinstance(data[k].get("tasks"), list)
        ]
        if slug_keys:
            sys.exit(
                f"No tasks loaded for --tag {tag!r}. This file uses top-level slug key(s): "
                f"{', '.join(sorted(slug_keys))}.\n"
                f"Pass the key that holds your task list, e.g. --tag {slug_keys[0]}"
            )

    git_root = git_repo_root_containing(tasks_path)

    if args.repo:
        repo = args.repo
        repo_url = f"https://github.com/{repo}"
    else:
        if git_root is None:
            sys.exit(
                f"tasks.json is not inside a git repository: {tasks_path.resolve()}\n"
                "Place the file in a clone, or pass --repo owner/name."
            )
        repo, repo_url = get_repo_info(cwd=git_root)


    print(f"Repository : {repo}")
    if git_root is not None:
        print(f"Git root     : {git_root}")

    print(f"Tasks file : {tasks_path}")
    print(f"Tag        : {tag}")
    review_count = sum(1 for t in tasks if is_review_task(t))
    build_count = len(tasks) - review_count
    print(f"Total tasks: {len(tasks)}  ({build_count} build, {review_count} review P*-R skipped)")
    if args.dry_run:
        print("Mode       : DRY RUN (no issues will be created)\n")
    else:
        print()

    # Pre-create all labels we'll need
    all_labels: set[str] = set()
    for task in tasks:
        if not is_review_task(task):
            all_labels.update(build_labels(task, tag))
    if not args.dry_run and all_labels:
        print(f"Ensuring labels exist: {', '.join(sorted(all_labels))}")
        ensure_labels_exist(all_labels, repo)
        print()

    # taskId (and stringified numeric id) -> (issue_number, issue_url)
    mapping: dict[str, tuple[int, str]] = {}
    created_issues = 0
    reused_issues = 0

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
        labels = build_labels(task, tag)

        stored = parse_stored_github_issue_metadata(task, repo_url)

        if args.dry_run:
            print(f"  Labels : {labels}")
            print(f"  Body   : {body[:120].replace(chr(10), ' ')}…")
            if stored:
                n, url = stored
                print(f"  -> existing #{n}  {url}  (dry-run: would reuse metadata)")
                if task_id:
                    mapping[task_id] = (n, url)
                if numeric_id is not None:
                    mapping[str(numeric_id)] = (n, url)
                reused_issues += 1
            else:
                title_hit = find_issue_by_exact_title(repo, title)
                if title_hit:
                    n, url = title_hit
                    print(f"  -> existing #{n}  {url}  (dry-run: would reuse, same title on GitHub)")
                    if task_id:
                        mapping[task_id] = (n, url)
                    if numeric_id is not None:
                        mapping[str(numeric_id)] = (n, url)
                    reused_issues += 1
                else:
                    fake_num = 1000 + idx
                    fake_url = f"{repo_url}/issues/{fake_num}"
                    if task_id:
                        mapping[task_id] = (fake_num, fake_url)
                    if numeric_id is not None:
                        mapping[str(numeric_id)] = (fake_num, fake_url)
                    created_issues += 1
            print()
            continue

        if stored:
            n, _stored_url = stored
            canonical_url = fetch_github_issue_url(repo, n)
            if canonical_url is not None:
                issue_number, issue_url = n, canonical_url
                print(f"  -> existing #{issue_number}  {issue_url}  (skip create, metadata)")
                if task_id:
                    mapping[task_id] = (issue_number, issue_url)
                if numeric_id is not None:
                    mapping[str(numeric_id)] = (issue_number, issue_url)
                apply_issue_to_task(task, issue_number, issue_url, update_prose=False)
                reused_issues += 1
                continue
            print(
                f"  ! Issue #{n} from metadata not found on GitHub; will try title search or create.",
                file=sys.stderr,
            )

        title_hit = find_issue_by_exact_title(repo, title)
        if title_hit:
            n, hit_url = title_hit
            issue_url = fetch_github_issue_url(repo, n) or hit_url
            print(f"  -> existing #{n}  {issue_url}  (skip create, same title on GitHub)")
            if task_id:
                mapping[task_id] = (n, issue_url)
            if numeric_id is not None:
                mapping[str(numeric_id)] = (n, issue_url)
            apply_issue_to_task(task, n, issue_url, update_prose=False)
            reused_issues += 1
            continue

        issue_number, issue_url = create_issue(title, body, labels, repo)
        print(f"  -> #{issue_number}  {issue_url}")

        if task_id:
            mapping[task_id] = (issue_number, issue_url)
        if numeric_id is not None:
            mapping[str(numeric_id)] = (issue_number, issue_url)

        apply_issue_to_task(task, issue_number, issue_url, update_prose=True)
        created_issues += 1

    # Write the updated tasks.json back
    if not args.dry_run:
        if isinstance(data, list):
            output_data = tasks
        elif isinstance(data.get("tasks"), dict):
            data["tasks"][tag] = tasks
            output_data = data
        elif tag_nested_tasks:
            data[tag]["tasks"] = tasks
            output_data = data
        elif tag in data:
            data[tag] = tasks
            output_data = data
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

    print(f"\nIssues in mapping: {len(seen)}")
    if args.dry_run:
        print(f"  (dry-run: would create ~{created_issues}, would reuse ~{reused_issues})")
    else:
        print(f"  Newly created this run: {created_issues}")
        print(f"  Reused (already on GitHub): {reused_issues}")
    if review_count:
        print(f"Review tasks skipped (no issue): {review_count}")


if __name__ == "__main__":
    main()
