#!/usr/bin/env bash
#
# Agentic Dev Cycle — Project Install Script
#
# Run this once from your project root after adding this repo as a submodule:
#
#   git submodule add <url> .agentic-dev-cycle
#   bash .agentic-dev-cycle/install.sh
#
# What it does:
#   1. Symlinks .claude/skills/ → <absolute path to this repo>/skills/
#   2. Bootstraps .dev_cycle/ in your project with all config templates
#   3. Adds .dev_cycle/ and .claude/skills to .gitignore
#   4. Does NOT overwrite existing config files (safe to re-run after updates)
#
# After install, run /init-dev-cycle in Claude Code to configure for your project.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"

# Safety check: ensure we're not running from inside the submodule itself
if [[ "$PROJECT_ROOT" == "$SCRIPT_DIR" ]]; then
  echo "Error: run this script from your project root, not from inside the submodule."
  echo "Usage: bash .agentic-dev-cycle/install.sh"
  exit 1
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
skip() { echo -e "${YELLOW}↷${NC} $1 (already exists — skipped)"; }

echo ""
echo "Agentic Dev Cycle — installing into $(basename "$PROJECT_ROOT")"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Symlink .claude/skills/
# ---------------------------------------------------------------------------

SKILLS_TARGET="$PROJECT_ROOT/.claude/skills"
SKILLS_SOURCE="$SCRIPT_DIR/skills"

mkdir -p "$PROJECT_ROOT/.claude"

if [[ -L "$SKILLS_TARGET" ]]; then
  skip ".claude/skills symlink"
elif [[ -d "$SKILLS_TARGET" ]]; then
  echo "Warning: .claude/skills/ exists as a real directory, not a symlink."
  echo "If you want to use this workflow's skills, back it up and re-run:"
  echo "  mv .claude/skills .claude/skills.bak && bash .agentic-dev-cycle/install.sh"
else
  ln -s "$SKILLS_SOURCE" "$SKILLS_TARGET"
  ok ".claude/skills → $SKILLS_SOURCE"
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
echo "  1. Open Claude Code in your project"
echo "  2. Run: /init-dev-cycle"
echo "     This configures .dev_cycle/project.md, gates_config.sh, and agent instructions"
echo "     for your specific tech stack."
echo "  3. Ensure gh CLI is authenticated: gh auth login"
echo "     (required for GitHub Issues integration)"
echo "  4. Commit the generated files:"
echo "     git add .dev_cycle/ .claude/skills"
echo "     git commit -m 'dev_cycle: add agentic dev cycle workflow'"
echo "     git push origin main"
echo ""
echo "  Note: .dev_cycle/ is gitignored by default. If you want your team to share"
echo "  workflow state, remove '.dev_cycle/' from .gitignore and commit it."
echo ""
echo "See .dev_cycle/workflow.md for the full development process."
