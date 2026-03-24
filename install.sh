#!/usr/bin/env bash
#
# Agentic Dev Cycle — Project Install Script
#
# Clone this repo once, then run it against any project:
#
#   git clone https://github.com/pequnio3/agentic_dev_cycle ~/tools/agentic-dev-cycle
#   bash ~/tools/agentic-dev-cycle/install.sh /path/to/your/project
#
# Or from inside your project root (no argument needed):
#
#   bash ~/tools/agentic-dev-cycle/install.sh
#
# What it does:
#   1. Copies core/ into .dev-cycle/core/ in the target project (includes create_issues.py)
#   2. Detects existing AI tool folders (.claude, .cursor, .agents, .gemini)
#      and wires skill hubs so each tool discovers the dev-cycle skills
#   3. Appends workflow routing to AGENTS.md
#   4. Adds .cursor/rules/dev-cycle.mdc (only if .cursor/ already exists)
#   5. Updates .gitignore
#
# Re-run after `git pull` in the tool repo to pick up changes.
# Set AGENTIC_DEV_CYCLE_NO_OVERWRITE=1 to skip overwriting existing files.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

if [[ "$PROJECT_ROOT" == "$SCRIPT_DIR" ]]; then
  echo "Error: target directory is the tool repo itself."
  echo "Usage: bash install.sh /path/to/your/project"
  exit 1
fi

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "Error: target directory does not exist: $PROJECT_ROOT"
  exit 1
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
skip() { echo -e "${YELLOW}↷${NC} $1 (already exists — skipped)"; }

OVERWRITE_INSTALL=true
if [[ "${AGENTIC_DEV_CYCLE_NO_OVERWRITE:-}" == "1" ]]; then
  OVERWRITE_INSTALL=false
fi

DEV_CYCLE_ROOT="$PROJECT_ROOT/.dev-cycle"
LEGACY_DEV_CYCLE_ROOT="$PROJECT_ROOT/.dev_cycle"

# Migrate legacy install directory (underscore) → .dev-cycle (hyphen)
if [[ -d "$LEGACY_DEV_CYCLE_ROOT" ]] && [[ ! -e "$DEV_CYCLE_ROOT" ]]; then
  mv "$LEGACY_DEV_CYCLE_ROOT" "$DEV_CYCLE_ROOT"
  ok "Renamed legacy .dev_cycle/ → .dev-cycle/"
fi
if [[ -d "$LEGACY_DEV_CYCLE_ROOT" ]] && [[ -d "$DEV_CYCLE_ROOT" ]]; then
  info "Both .dev_cycle and .dev-cycle exist — using .dev-cycle/. Remove .dev_cycle/ manually if obsolete."
fi

# ---------------------------------------------------------------------------
# link_skill_hub — wire a per-tool skill hub to .dev-cycle/core/skills
# ---------------------------------------------------------------------------
#
# Creates:
#   $hub/dev-cycle    → ../../.dev-cycle/core/skills        (bundle)
#   $hub/$skill_name  → ../../.dev-cycle/core/skills/$name  (flat per-skill)
#
# AI tools scan immediate children of their skills dir, so both the bundle
# and the flat per-skill symlinks are needed for discovery.
link_skill_hub() {
  local hub_rel="$1"
  local hub_abs="$PROJECT_ROOT/$hub_rel"
  local skill_source="$DEV_CYCLE_ROOT/core/skills"

  mkdir -p "$hub_abs"

  # Drop legacy bundle symlink name (underscore)
  if [[ -L "$hub_abs/dev_cycle" ]]; then
    rm "$hub_abs/dev_cycle"
    ok "Removed legacy $hub_rel/dev_cycle symlink"
  fi

  # Remove stale symlinks from old installs (pointed at */skills without /core/)
  for existing_link in "$hub_abs"/*; do
    [[ -L "$existing_link" ]] || continue
    local target
    target="$(readlink "$existing_link")"
    if [[ "$target" == *".dev_cycle/skills"* ]] && [[ "$target" != *".dev_cycle/core/skills"* ]]; then
      rm "$existing_link"
      ok "Removed stale link: $hub_rel/$(basename "$existing_link")"
    fi
    if [[ "$target" == *".dev-cycle/skills"* ]] && [[ "$target" != *".dev-cycle/core/skills"* ]]; then
      rm "$existing_link"
      ok "Removed stale link: $hub_rel/$(basename "$existing_link")"
    fi
  done

  # Bundle link: dev-cycle → all skills
  local bundle="$hub_abs/dev-cycle"
  if [[ -e "$bundle" ]] && [[ ! -L "$bundle" ]]; then
    echo "Warning: $hub_rel/dev-cycle exists and is not a symlink — not overwriting."
  elif $OVERWRITE_INSTALL || [[ ! -e "$bundle" ]]; then
    ln -sfn "../../.dev-cycle/core/skills" "$bundle"
    ok "$hub_rel/dev-cycle → .dev-cycle/core/skills"
  else
    skip "$hub_rel/dev-cycle"
  fi

  # Per-skill flat links (AI tools discover immediate children)
  local potential name link
  for potential in "$skill_source"/*/; do
    [[ -d "$potential" ]] || continue
    [[ -f "$potential/SKILL.md" ]] || continue
    name="$(basename "$potential")"
    link="$hub_abs/$name"
    if [[ -e "$link" ]] && [[ ! -L "$link" ]]; then
      echo "Warning: $hub_rel/$name exists and is not a symlink — not overwriting."
    elif $OVERWRITE_INSTALL || [[ ! -e "$link" ]]; then
      ln -sfn "../../.dev-cycle/core/skills/$name" "$link"
      ok "$hub_rel/$name → .dev-cycle/core/skills/$name"
    elif [[ ! -e "$link" ]]; then
      ln -sfn "../../.dev-cycle/core/skills/$name" "$link"
      ok "$hub_rel/$name → .dev-cycle/core/skills/$name"
    else
      skip "$hub_rel/$name"
    fi
  done
}

echo ""
echo "Agentic Dev Cycle — installing into $(basename "$PROJECT_ROOT")"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Copy core/ into .dev-cycle/core/
# ---------------------------------------------------------------------------

CORE_SRC="$SCRIPT_DIR/core"
CORE_DST="$DEV_CYCLE_ROOT/core"

if [[ ! -d "$CORE_SRC" ]]; then
  echo "Error: core/ directory not found in tool repo: $CORE_SRC"
  exit 1
fi

mkdir -p "$DEV_CYCLE_ROOT"

# Remove legacy skills symlink if present (old installs pointed here)
if [[ -L "$PROJECT_ROOT/.dev_cycle/skills" ]]; then
  rm "$PROJECT_ROOT/.dev_cycle/skills"
  ok "Removed legacy .dev_cycle/skills symlink"
fi
if [[ -L "$DEV_CYCLE_ROOT/skills" ]]; then
  rm "$DEV_CYCLE_ROOT/skills"
  ok "Removed legacy .dev-cycle/skills symlink"
fi

if $OVERWRITE_INSTALL; then
  rm -rf "$CORE_DST"
  cp -R "$CORE_SRC" "$CORE_DST"
  ok ".dev-cycle/core/ — copied from tool repo (refreshed)"
elif [[ ! -d "$CORE_DST" ]]; then
  cp -R "$CORE_SRC" "$CORE_DST"
  ok ".dev-cycle/core/ — copied from tool repo"
else
  skip ".dev-cycle/core/"
fi

# ---------------------------------------------------------------------------
# Step 2: Detect AI tool folders and link skill hubs
# ---------------------------------------------------------------------------

AI_TOOLS=(.claude .cursor .agents .gemini)
DETECTED_TOOLS=()

for tool_dir in "${AI_TOOLS[@]}"; do
  if [[ -d "$PROJECT_ROOT/$tool_dir" ]]; then
    DETECTED_TOOLS+=("$tool_dir")
  fi
done

echo ""
if [[ ${#DETECTED_TOOLS[@]} -eq 0 ]]; then
  info "No AI tool folders detected (${AI_TOOLS[*]})."
  info "Skill hub linking skipped. Create a tool config folder and re-run to link."
else
  info "Detected AI tools: ${DETECTED_TOOLS[*]}"
  for tool_dir in "${DETECTED_TOOLS[@]}"; do
    # Remove legacy: entire skills dir was a single symlink in older installs
    local_skills="$PROJECT_ROOT/$tool_dir/skills"
    if [[ -L "$local_skills" ]]; then
      rm "$local_skills"
      ok "Removed legacy $tool_dir/skills symlink"
    fi
    link_skill_hub "$tool_dir/skills"
  done
fi

# ---------------------------------------------------------------------------
# Step 3: AGENTS.md (Codex CLI + Gemini CLI)
# ---------------------------------------------------------------------------

AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
AGENTS_MARKER="<!-- agentic-dev-cycle -->"
AGENTS_END="<!-- /agentic-dev-cycle -->"

# Build dynamic skill routing table from discovered skills
SKILL_TABLE=""
for skill_dir in "$CORE_SRC"/skills/*/; do
  [[ -d "$skill_dir" ]] || continue
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  skill_name="$(basename "$skill_dir")"
  pretty_name="${skill_name//-/ }"
  pretty_name="${pretty_name//_/ }"
  pretty_name="${pretty_name^}"
  SKILL_TABLE+="| ${pretty_name} | \`.dev-cycle/core/skills/${skill_name}/SKILL.md\` |
"
done

if ! $OVERWRITE_INSTALL && [[ -f "$AGENTS_FILE" ]] && grep -qF "$AGENTS_MARKER" "$AGENTS_FILE"; then
  skip "AGENTS.md workflow section"
else
  # Strip existing agentic-dev-cycle block if present
  if [[ -f "$AGENTS_FILE" ]]; then
    agents_tmp="$(mktemp)"
    awk '
      /^<!-- agentic-dev-cycle -->$/ { skip=1; next }
      /^<!-- \/agentic-dev-cycle -->$/ { skip=0; next }
      skip { next }
      { print }
    ' "$AGENTS_FILE" > "$agents_tmp"
    mv "$agents_tmp" "$AGENTS_FILE"
  else
    touch "$AGENTS_FILE"
  fi
  cat >> "$AGENTS_FILE" <<EOF

$AGENTS_MARKER
## Agentic Dev Cycle

This project uses a structured development workflow powered by skills
in \`.dev-cycle/core/skills/\`. When asked to perform any of the
following tasks, read the corresponding skill file first.

| Task | Instructions |
|------|-------------|
${SKILL_TABLE}
**Utilities:** \`.dev-cycle/core/\` contains scripts (e.g. \`create_issues.py\`)
for workflow automation.

$AGENTS_END
EOF
  ok "AGENTS.md — workflow section updated"
fi

# ---------------------------------------------------------------------------
# Step 4: .cursor/rules/dev-cycle.mdc (only if .cursor/ exists)
# ---------------------------------------------------------------------------

if [[ -d "$PROJECT_ROOT/.cursor" ]]; then
  CURSOR_RULES_DIR="$PROJECT_ROOT/.cursor/rules"
  CURSOR_RULE_FILE="$CURSOR_RULES_DIR/dev-cycle.mdc"

  mkdir -p "$CURSOR_RULES_DIR"

  CURSOR_SKILL_TABLE=""
  for skill_dir in "$CORE_SRC"/skills/*/; do
    [[ -d "$skill_dir" ]] || continue
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    skill_name="$(basename "$skill_dir")"
    pretty_name="${skill_name//-/ }"
    pretty_name="${pretty_name//_/ }"
    pretty_name="${pretty_name^}"
    CURSOR_SKILL_TABLE+="| ${pretty_name} | \`.dev-cycle/core/skills/${skill_name}/SKILL.md\` |
"
  done

  if ! $OVERWRITE_INSTALL && [[ -f "$CURSOR_RULE_FILE" ]]; then
    skip ".cursor/rules/dev-cycle.mdc"
  else
    cat > "$CURSOR_RULE_FILE" <<EOF
---
description: Agentic dev cycle workflow routing
alwaysApply: true
---

## Agentic Dev Cycle

This project uses a structured development workflow powered by skills
in \`.dev-cycle/core/skills/\`. When asked to perform any of the
following tasks, read the corresponding skill file first.

| Task | Instructions |
|------|-------------|
${CURSOR_SKILL_TABLE}
**Utilities:** \`.dev-cycle/core/\` contains scripts (e.g. \`create_issues.py\`)
for workflow automation.
EOF
    ok ".cursor/rules/dev-cycle.mdc"
  fi
fi

# ---------------------------------------------------------------------------
# Step 5: Check GitHub CLI
# ---------------------------------------------------------------------------

echo ""
info "Checking GitHub CLI..."
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  ok "gh CLI authenticated — GitHub Issues integration available"
elif command -v gh &>/dev/null; then
  info "gh CLI found but not authenticated. Run: gh auth login"
else
  info "gh CLI not found. Install from https://cli.github.com/"
fi

# ---------------------------------------------------------------------------
# Step 6: Update .gitignore
# ---------------------------------------------------------------------------

GITIGNORE="$PROJECT_ROOT/.gitignore"

add_gitignore_entry() {
  local entry="$1"
  if [[ ! -f "$GITIGNORE" ]]; then
    echo "$entry" > "$GITIGNORE"
    ok "Created .gitignore with: $entry"
  elif ! grep -qF "$entry" "$GITIGNORE"; then
    echo "" >> "$GITIGNORE"
    echo "$entry" >> "$GITIGNORE"
    ok "Added to .gitignore: $entry"
  else
    skip ".gitignore entry: $entry"
  fi
}

echo ""
info "Updating .gitignore..."

if [[ ! -f "$GITIGNORE" ]] || ! grep -qF "Agentic dev cycle" "$GITIGNORE"; then
  if [[ ! -f "$GITIGNORE" ]]; then
    echo "# Agentic dev cycle" > "$GITIGNORE"
  else
    printf "\n# Agentic dev cycle\n" >> "$GITIGNORE"
  fi
fi

add_gitignore_entry ".dev-cycle/"
add_gitignore_entry ".dev_cycle/"

# Only add skill hub ignores for detected tools
if [[ ${#DETECTED_TOOLS[@]} -gt 0 ]]; then
  for tool_dir in "${DETECTED_TOOLS[@]}"; do
    add_gitignore_entry "$tool_dir/skills"
  done
fi

echo ""
echo "  Note: .dev-cycle/ is gitignored by default — your workflow state is private."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "${GREEN}Install complete.${NC}"
echo ""
if [[ ${#DETECTED_TOOLS[@]} -gt 0 ]]; then
  echo "  Linked AI tools: ${DETECTED_TOOLS[*]}"
else
  echo "  No AI tool folders found. To link skills for a tool, create its"
  echo "  config folder (e.g. mkdir .claude) and re-run this script."
fi
echo ""
echo "  Skills:    .dev-cycle/core/skills/"
echo "  Utilities: .dev-cycle/core/ (e.g. create_issues.py)"
echo ""
echo "  To add a new AI tool later, create its folder and re-run:"
echo "    bash $SCRIPT_DIR/install.sh $PROJECT_ROOT"
echo ""
