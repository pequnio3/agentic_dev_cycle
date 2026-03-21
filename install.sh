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
#   0.  pip install -e core/langgraph_design (dev-cycle-design-graph, dev-cycle-init-graph CLIs)
#       Skip with AGENTIC_DEV_CYCLE_SKIP_PIP=1
#   1a. Symlinks project .dev_cycle/skills → core/skills in this repo (canonical bundle)
#        and wires per-tool hubs: .claude/skills/dev_cycle, .cursor/skills/dev_cycle,
#        .agents/skills/dev_cycle, .gemini/skills/dev_cycle — each also gets flat
#        per-skill symlinks so Claude/Cursor discover /design, /build, etc.
#   1b. Appends workflow routing to AGENTS.md  (Codex CLI + Gemini CLI)
#   2.  Bootstraps .dev_cycle/ — copies templates and reference docs (overwrites on re-run)
#   3.  Adds .dev_cycle/ and skill hub paths to .gitignore
#   4.  Refreshes AGENTS.md workflow block + .cursor/rules/dev-cycle.mdc from this tool
#
# Re-run after `git pull` in the tool repo to pick up workflow changes, then run
# /init-dev-cycle (or "init dev cycle") to regenerate project-specific files.
# Set AGENTIC_DEV_CYCLE_NO_OVERWRITE=1 to restore old skip-if-exists behavior for files only.
#
# After install, run /init-dev-cycle (Claude Code), or ask your AI agent
# to "init dev cycle" (Codex / Gemini) to configure for your project.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

# Installing into the tool repo itself is allowed: creates .dev_cycle/ next to core/
# so you can dogfood /design and /build on this repository.

# Safety check: ensure target exists
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

# Default: overwrite templates and routing files so `git pull` + reinstall refreshes the core.
OVERWRITE_INSTALL=true
if [[ "${AGENTIC_DEV_CYCLE_NO_OVERWRITE:-}" == "1" ]]; then
  OVERWRITE_INSTALL=false
fi

# Canonical skills live under core/skills in this repo; installed projects use .dev_cycle/skills → core/skills.
# Each tool hub gets dev_cycle → .dev_cycle/skills plus one symlink per skill at the
# hub root (Claude/Cursor scan immediate children; dev_cycle/ has no SKILL.md at root).
link_skill_hub() {
  local hub_rel="$1"
  local hub_abs="$PROJECT_ROOT/$hub_rel"
  local skill_root="$SCRIPT_DIR/core/skills"

  mkdir -p "$hub_abs"

  local bundle="$hub_abs/dev_cycle"
  if [[ -e "$bundle" ]] && [[ ! -L "$bundle" ]]; then
    echo "Warning: $hub_rel/dev_cycle exists and is not a symlink — not overwriting."
  elif $OVERWRITE_INSTALL; then
    ln -sfn "../../.dev_cycle/skills" "$bundle"
    ok "$hub_rel/dev_cycle → .dev_cycle/skills"
  elif [[ ! -e "$bundle" ]]; then
    ln -sfn "../../.dev_cycle/skills" "$bundle"
    ok "$hub_rel/dev_cycle → .dev_cycle/skills"
  else
    skip "$hub_rel/dev_cycle"
  fi

  local potential name link
  for potential in "$skill_root"/*/; do
    [[ -d "$potential" ]] || continue
    [[ -f "$potential/SKILL.md" ]] || continue
    name="$(basename "$potential")"
    link="$hub_abs/$name"
    if [[ -e "$link" ]] && [[ ! -L "$link" ]]; then
      echo "Warning: $hub_rel/$name exists and is not a symlink — not overwriting."
    elif $OVERWRITE_INSTALL; then
      ln -sfn "../../.dev_cycle/skills/$name" "$link"
      ok "$hub_rel/$name → .dev_cycle/skills/$name"
    elif [[ ! -e "$link" ]]; then
      ln -sfn "../../.dev_cycle/skills/$name" "$link"
      ok "$hub_rel/$name → .dev_cycle/skills/$name"
    else
      skip "$hub_rel/$name"
    fi
  done
}

echo ""
echo "Agentic Dev Cycle — installing into $(basename "$PROJECT_ROOT")"
echo ""

# ---------------------------------------------------------------------------
# Step 1a: .dev_cycle/skills + per-tool skill hubs
# ---------------------------------------------------------------------------

mkdir -p "$PROJECT_ROOT/.dev_cycle"

DEV_CYCLE_SKILLS="$PROJECT_ROOT/.dev_cycle/skills"
BUNDLED_SKILLS="$SCRIPT_DIR/core/skills"

if [[ -d "$DEV_CYCLE_SKILLS" ]] && [[ ! -L "$DEV_CYCLE_SKILLS" ]]; then
  echo "Warning: .dev_cycle/skills/ exists as a real directory, not a symlink."
  echo "Back it up and re-run install, or remove it if you want the bundled skills."
elif $OVERWRITE_INSTALL && [[ -L "$DEV_CYCLE_SKILLS" ]]; then
  ln -sfn "$BUNDLED_SKILLS" "$DEV_CYCLE_SKILLS"
  ok ".dev_cycle/skills → $BUNDLED_SKILLS (refreshed)"
elif [[ ! -e "$DEV_CYCLE_SKILLS" ]]; then
  ln -sfn "$BUNDLED_SKILLS" "$DEV_CYCLE_SKILLS"
  ok ".dev_cycle/skills → $BUNDLED_SKILLS"
else
  skip ".dev_cycle/skills symlink"
fi

# Legacy: entire .claude/skills was a single symlink to the tool skills dir
CLAUDE_SKILLS_DIR="$PROJECT_ROOT/.claude/skills"
mkdir -p "$PROJECT_ROOT/.claude"
if [[ -L "$CLAUDE_SKILLS_DIR" ]]; then
  rm "$CLAUDE_SKILLS_DIR"
  ok "Removed legacy .claude/skills symlink (replaced with skill hub layout)"
fi

info "Linking skill hubs (Claude, Cursor, Codex/Gemini .agents, Gemini .gemini)..."
link_skill_hub ".claude/skills"
link_skill_hub ".cursor/skills"
link_skill_hub ".agents/skills"
link_skill_hub ".gemini/skills"

# ---------------------------------------------------------------------------
# Step 1b: AGENTS.md  (Codex CLI + Gemini CLI)
# ---------------------------------------------------------------------------
#
# Both Codex CLI and Gemini CLI read AGENTS.md from the project root.
# With overwrite: strip the old workflow block (start/end markers) and append fresh.
#
AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
AGENTS_MARKER="<!-- agentic-dev-cycle -->"
AGENTS_END="<!-- /agentic-dev-cycle -->"

if ! $OVERWRITE_INSTALL && [[ -f "$AGENTS_FILE" ]] && grep -qF "$AGENTS_MARKER" "$AGENTS_FILE"; then
  skip "AGENTS.md (workflow section — skipped; rerun without AGENTIC_DEV_CYCLE_NO_OVERWRITE=1 to refresh)"
else
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
## Agentic Dev Cycle Workflow

This project uses a structured development workflow. When asked to perform
any of the following tasks, read the corresponding instructions file first.

| Task | Instructions |
|------|-------------|
| Design a feature / expand an idea | \`.dev_cycle/agents/design/\` (\`base.md\` + \`custom.md\`) |
| Build a GitHub Issue | \`.dev_cycle/agents/build/\` |
| Review a feature branch | \`.dev_cycle/agents/review/\` |
| Fix a bug or PR | \`.dev_cycle/agents/fix/\` |
| Deploy / start dev servers | \`.dev_cycle/agents/deploy/\` |
| Complete a merged work order | \`.dev_cycle/skills/complete/SKILL.md\` |

**Project config** (tech stack, architecture patterns, gate commands):
\`.dev_cycle/project.yaml\`

**Work orders:** GitHub Issues labeled \`dev-cycle:build\`
**Past decisions:** GitHub Issues labeled \`dev-cycle:decision\` — always scan
these before starting work on a new feature.

$AGENTS_END
EOF
  ok "AGENTS.md — workflow section updated"
fi

# ---------------------------------------------------------------------------
# Step 1c: .cursor/rules/dev-cycle.mdc  (Cursor Composer)
# ---------------------------------------------------------------------------
#
# Cursor reads .cursor/rules/*.mdc files automatically in every Composer
# session when alwaysApply: true is set. This gives Composer the workflow
# routing without the user needing to manually reference files.
#
CURSOR_RULES_DIR="$PROJECT_ROOT/.cursor/rules"
CURSOR_RULE_FILE="$CURSOR_RULES_DIR/dev-cycle.mdc"

mkdir -p "$CURSOR_RULES_DIR"

if ! $OVERWRITE_INSTALL && [[ -f "$CURSOR_RULE_FILE" ]]; then
  skip ".cursor/rules/dev-cycle.mdc"
else
  cat > "$CURSOR_RULE_FILE" <<'EOF'
---
description: Agentic dev cycle workflow routing
alwaysApply: true
---

## Agentic Dev Cycle Workflow

This project uses a structured development workflow. When asked to perform
any of the following tasks, read the corresponding instructions file first
before doing anything else.

| Task | Instructions |
|------|-------------|
| Design a feature / expand an idea | `.dev_cycle/agents/design/` |
| Build a GitHub Issue | `.dev_cycle/agents/build/` |
| Review a feature branch | `.dev_cycle/agents/review/` |
| Fix a bug or PR | `.dev_cycle/agents/fix/` |
| Deploy / start dev servers | `.dev_cycle/agents/deploy/` |
| Complete a merged work order | `.dev_cycle/skills/complete/SKILL.md` |

**Project config** (tech stack, architecture patterns, gate commands):
`.dev_cycle/project.yaml`

**Work orders:** GitHub Issues labeled `dev-cycle:build`
**Past decisions:** GitHub Issues labeled `dev-cycle:decision` — scan
these before starting work on any new feature.
EOF
  ok ".cursor/rules/dev-cycle.mdc"
fi

# ---------------------------------------------------------------------------
# Step 2: Check GitHub CLI
# ---------------------------------------------------------------------------

echo ""
info "Checking GitHub CLI..."
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  ok "gh CLI authenticated — GitHub Issues integration available"
  info "The dev-cycle:decision label will be created automatically by /complete on first use."
elif command -v gh &>/dev/null; then
  info "gh CLI found but not authenticated. Run: gh auth login"
  info "GitHub Issues integration requires auth to create/manage issues."
  info "The dev-cycle:decision label will be created automatically by /complete on first use."
else
  info "gh CLI not found. Install from https://cli.github.com/"
  info "GitHub Issues integration requires gh CLI to be installed and authenticated."
fi

# ---------------------------------------------------------------------------
# Step 3: Create .dev_cycle/ directory structure
# ---------------------------------------------------------------------------

for dir in \
  .dev_cycle/design \
  .dev_cycle/agents
do
  if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
    mkdir -p "$PROJECT_ROOT/$dir"
    touch "$PROJECT_ROOT/$dir/.gitkeep"
    ok "Created $dir/"
  fi
done

# ---------------------------------------------------------------------------
# Step 4: Copy template files (overwrite by default)
# ---------------------------------------------------------------------------

copy_template() {
  local src="$1"
  local dst="$2"
  if ! $OVERWRITE_INSTALL && [[ -f "$dst" ]]; then
    skip "$(basename "$dst")"
    return
  fi
  cp "$src" "$dst"
  ok "$(basename "$dst")"
}

if $OVERWRITE_INSTALL; then
  info "Refreshing .dev_cycle templates from tool (overwrites existing copies)."
  info "Re-run /init-dev-cycle afterward to regenerate project-specific project.yaml, gates_config.sh, and agents."
fi

info "Copying config templates to .dev_cycle/..."
copy_template "$SCRIPT_DIR/core/gates.sh"        "$PROJECT_ROOT/.dev_cycle/gates.sh"
copy_template "$SCRIPT_DIR/core/gates_config.sh" "$PROJECT_ROOT/.dev_cycle/gates_config.sh"
copy_template "$SCRIPT_DIR/core/project.yaml"    "$PROJECT_ROOT/.dev_cycle/project.yaml"

chmod +x "$PROJECT_ROOT/.dev_cycle/gates.sh"

# Agent prompts: <agent>/{base,custom}.md — base from tool; custom is usually edited by /init-dev-cycle
for agent in init design build review fix deploy; do
  mkdir -p "$PROJECT_ROOT/.dev_cycle/agents/$agent"
  copy_template \
    "$SCRIPT_DIR/core/agents/$agent/base.md" \
    "$PROJECT_ROOT/.dev_cycle/agents/$agent/base.md"
  copy_template \
    "$SCRIPT_DIR/core/agents/$agent/custom.md" \
    "$PROJECT_ROOT/.dev_cycle/agents/$agent/custom.md"
done

# Decisions are stored as GitHub Issues labeled "dev-cycle:decision"
# No local file needed — created automatically by /complete

# Copy workflow docs (reference — overwrite when install overwrites)
for doc in workflow.md; do
  if ! $OVERWRITE_INSTALL && [[ -f "$PROJECT_ROOT/.dev_cycle/$doc" ]]; then
    skip "$doc"
  else
    cp "$SCRIPT_DIR/core/$doc" "$PROJECT_ROOT/.dev_cycle/$doc"
    ok "$doc"
  fi
done

# ---------------------------------------------------------------------------
# Step 4b: LangGraph package (CLI entry points for /design and /init-dev-cycle graphs)
# ---------------------------------------------------------------------------

LANGGRAPH_PKG="$SCRIPT_DIR/core/langgraph_design"
if [[ "${AGENTIC_DEV_CYCLE_SKIP_PIP:-}" == "1" ]]; then
  skip "pip install langgraph_design (AGENTIC_DEV_CYCLE_SKIP_PIP=1)"
elif [[ -d "$LANGGRAPH_PKG" && -f "$LANGGRAPH_PKG/pyproject.toml" ]]; then
  echo ""
  info "Installing LangGraph package (editable install for CLIs)..."
  if python3 -m pip install -e "$LANGGRAPH_PKG"; then
    ok "pip install -e core/langgraph_design (dev-cycle-design-graph, dev-cycle-init-graph)"
  else
    echo -e "${YELLOW}Warning:${NC} pip install failed. Install manually when needed:"
    echo "  python3 -m pip install -e \"$LANGGRAPH_PKG\""
  fi
else
  echo -e "${YELLOW}Warning:${NC} $LANGGRAPH_PKG missing — skipping pip install."
fi

# ---------------------------------------------------------------------------
# Step 5: Update .gitignore
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

# Add a header comment if we're adding our entries
if [[ ! -f "$GITIGNORE" ]] || ! grep -qF "Agentic dev cycle" "$GITIGNORE"; then
  if [[ ! -f "$GITIGNORE" ]]; then
    echo "# Agentic dev cycle" > "$GITIGNORE"
  else
    printf "\n# Agentic dev cycle\n" >> "$GITIGNORE"
  fi
fi

add_gitignore_entry ".dev_cycle/"
add_gitignore_entry ".claude/skills"
add_gitignore_entry ".cursor/skills"
add_gitignore_entry ".agents/skills"
add_gitignore_entry ".gemini/skills"

# AGENTS.md and .cursor/rules/dev-cycle.mdc are intentionally NOT gitignored
# — commit them so all team members get workflow routing regardless of their AI tool.

echo ""
echo "  Note: .dev_cycle/ is gitignored by default — your workflow state is private."
echo "  Teams who want shared workflow state: remove '.dev_cycle/' from .gitignore"
echo "  and commit it to main."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "${GREEN}Install complete.${NC}"
echo ""
if $OVERWRITE_INSTALL; then
  echo "  Templates and routing were refreshed from this tool. If this was an upgrade,"
  echo "  run /init-dev-cycle (or \"init dev cycle\") again to regenerate project-specific"
  echo "  project.yaml, gates_config.sh, and agents/<name>/{base,custom}.md."
  echo ""
fi
echo "Next steps:"
echo "  0. LangGraph CLIs should be on PATH (pip install ran above). Verify:"
echo "       dev-cycle-design-graph --help"
echo "       dev-cycle-init-graph --help"
echo ""
echo "  1. Configure for your project:"
echo "     Claude Code:  open project, run /init-dev-cycle"
echo "     Cursor:       open Composer, type 'init dev cycle'"
echo "     Codex CLI:    codex 'init dev cycle'"
echo "     Gemini CLI:   gemini 'init dev cycle'"
echo "     This generates .dev_cycle/project.yaml, gates_config.sh, and agent instructions."
echo ""
echo "  2. Ensure gh CLI is authenticated: gh auth login"
echo "     (required for GitHub Issues integration)"
echo ""
echo "  3. Commit the generated files:"
echo "     git add .dev_cycle/ .claude/skills AGENTS.md .cursor/rules/dev-cycle.mdc"
echo "     git commit -m 'dev_cycle: add agentic dev cycle workflow'"
echo "     git push origin main"
echo ""
echo "  Note: .dev_cycle/ is gitignored by default (workflow state is private)."
echo "  Teams: remove '.dev_cycle/' from .gitignore and commit it to share."
echo "  AGENTS.md is committed — Codex/Gemini users get workflow routing automatically."
echo ""
echo "See .dev_cycle/workflow.md for the full development process."
