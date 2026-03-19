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
#   1a. Symlinks .dev_cycle/skills → dev_cycle/skills in this repo (canonical copy)
#        and wires per-tool hubs: .claude/skills/dev_cycle, .cursor/skills/dev_cycle,
#        .agents/skills/dev_cycle, .gemini/skills/dev_cycle — each also gets flat
#        per-skill symlinks so Claude/Cursor discover /design, /build, etc.
#   1b. Appends workflow routing to AGENTS.md  (Codex CLI + Gemini CLI)
#   2.  Bootstraps .dev_cycle/ in your project with all config templates
#   3.  Adds .dev_cycle/ and skill hub paths to .gitignore
#   4.  Does NOT overwrite existing config files (safe to re-run after updates)
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

# Safety check: ensure we're not installing into the tool repo itself
if [[ "$PROJECT_ROOT" == "$SCRIPT_DIR" ]]; then
  echo "Error: target directory is the tool repo itself."
  echo "Usage: bash install.sh /path/to/your/project"
  exit 1
fi

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

# Canonical skills live under .dev_cycle/skills (points at this repo's dev_cycle/skills).
# Each tool hub gets dev_cycle → .dev_cycle/skills plus one symlink per skill at the
# hub root (Claude/Cursor scan immediate children; dev_cycle/ has no SKILL.md at root).
link_skill_hub() {
  local hub_rel="$1"
  local hub_abs="$PROJECT_ROOT/$hub_rel"
  local skill_root="$SCRIPT_DIR/dev_cycle/skills"

  mkdir -p "$hub_abs"

  local bundle="$hub_abs/dev_cycle"
  if [[ -L "$bundle" ]]; then
    skip "$hub_rel/dev_cycle"
  elif [[ -e "$bundle" ]]; then
    echo "Warning: $hub_rel/dev_cycle exists and is not a symlink — not overwriting."
  else
    ln -s "../../.dev_cycle/skills" "$bundle"
    ok "$hub_rel/dev_cycle → .dev_cycle/skills"
  fi

  local potential name link
  for potential in "$skill_root"/*/; do
    [[ -d "$potential" ]] || continue
    [[ -f "$potential/SKILL.md" ]] || continue
    name="$(basename "$potential")"
    link="$hub_abs/$name"
    if [[ -L "$link" ]]; then
      skip "$hub_rel/$name"
    elif [[ -e "$link" ]]; then
      echo "Warning: $hub_rel/$name exists and is not a symlink — not overwriting."
    else
      ln -s "../../.dev_cycle/skills/$name" "$link"
      ok "$hub_rel/$name → .dev_cycle/skills/$name"
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
BUNDLED_SKILLS="$SCRIPT_DIR/dev_cycle/skills"

if [[ -L "$DEV_CYCLE_SKILLS" ]]; then
  skip ".dev_cycle/skills symlink"
elif [[ -d "$DEV_CYCLE_SKILLS" ]] && [[ ! -L "$DEV_CYCLE_SKILLS" ]]; then
  echo "Warning: .dev_cycle/skills/ exists as a real directory, not a symlink."
  echo "Back it up and re-run install, or remove it if you want the bundled skills."
else
  ln -s "$BUNDLED_SKILLS" "$DEV_CYCLE_SKILLS"
  ok ".dev_cycle/skills → $BUNDLED_SKILLS"
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
# Both Codex CLI and Gemini CLI read AGENTS.md automatically from the project
# root. We append a workflow section rather than overwrite, so existing content
# is preserved.
#
AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
AGENTS_MARKER="<!-- agentic-dev-cycle -->"

if [[ -f "$AGENTS_FILE" ]] && grep -qF "$AGENTS_MARKER" "$AGENTS_FILE"; then
  skip "AGENTS.md (workflow section already present)"
else
  cat >> "$AGENTS_FILE" <<EOF

$AGENTS_MARKER
## Agentic Dev Cycle Workflow

This project uses a structured development workflow. When asked to perform
any of the following tasks, read the corresponding instructions file first.

| Task | Instructions |
|------|-------------|
| Design a feature / expand an idea | \`.dev_cycle/agents/design_agent.md\` |
| Build a GitHub Issue | \`.dev_cycle/agents/build_agent.md\` |
| Review a feature branch | \`.dev_cycle/agents/review_agent.md\` |
| Fix a bug or PR | \`.dev_cycle/agents/fix_agent.md\` |
| Deploy / start dev servers | \`.dev_cycle/agents/deploy_agent.md\` |
| Complete a merged work order | \`.dev_cycle/skills/complete/SKILL.md\` |

**Project config** (tech stack, architecture patterns, gate commands):
\`.dev_cycle/project.md\`

**Work orders:** GitHub Issues labeled \`dev-cycle:build\`
**Past decisions:** GitHub Issues labeled \`dev-cycle:decision\` — always scan
these before starting work on a new feature.
EOF
  ok "AGENTS.md — workflow section appended"
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

if [[ -f "$CURSOR_RULE_FILE" ]]; then
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
| Design a feature / expand an idea | `.dev_cycle/agents/design_agent.md` |
| Build a GitHub Issue | `.dev_cycle/agents/build_agent.md` |
| Review a feature branch | `.dev_cycle/agents/review_agent.md` |
| Fix a bug or PR | `.dev_cycle/agents/fix_agent.md` |
| Deploy / start dev servers | `.dev_cycle/agents/deploy_agent.md` |
| Complete a merged work order | `.dev_cycle/skills/complete/SKILL.md` |

**Project config** (tech stack, architecture patterns, gate commands):
`.dev_cycle/project.md`

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
# Step 4: Copy template files (skip if already present)
# ---------------------------------------------------------------------------

copy_template() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$dst" ]]; then
    cp "$src" "$dst"
    ok "$(basename "$dst")"
  else
    skip "$(basename "$dst")"
  fi
}

info "Copying config templates to .dev_cycle/..."
copy_template "$SCRIPT_DIR/dev_cycle/gates.sh"        "$PROJECT_ROOT/.dev_cycle/gates.sh"
copy_template "$SCRIPT_DIR/dev_cycle/gates_config.sh" "$PROJECT_ROOT/.dev_cycle/gates_config.sh"
copy_template "$SCRIPT_DIR/dev_cycle/project.md"      "$PROJECT_ROOT/.dev_cycle/project.md"

chmod +x "$PROJECT_ROOT/.dev_cycle/gates.sh"

# Copy generic agent instruction files (only if agents/ is empty)
for prompt in design_agent build_agent review_agent fix_agent deploy_agent; do
  copy_template \
    "$SCRIPT_DIR/dev_cycle/agents/${prompt}.md" \
    "$PROJECT_ROOT/.dev_cycle/agents/${prompt}.md"
done

# Decisions are stored as GitHub Issues labeled "dev-cycle:decision"
# No local file needed — created automatically by /complete

# Copy workflow docs (always take from submodule — these are reference, not config)
for doc in workflow.md; do
  if [[ ! -f "$PROJECT_ROOT/.dev_cycle/$doc" ]]; then
    cp "$SCRIPT_DIR/dev_cycle/$doc" "$PROJECT_ROOT/.dev_cycle/$doc"
    ok "$doc"
  fi
done

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
echo "Next steps:"
echo "  1. Configure for your project:"
echo "     Claude Code:  open project, run /init-dev-cycle"
echo "     Cursor:       open Composer, type 'init dev cycle'"
echo "     Codex CLI:    codex 'init dev cycle'"
echo "     Gemini CLI:   gemini 'init dev cycle'"
echo "     This generates .dev_cycle/project.md, gates_config.sh, and agent instructions."
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
