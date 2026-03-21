#!/bin/bash
# Development cycle verification gates
# Usage: ./.dev_cycle/gates.sh [iteration|pre-pr|final]
#
# Project-specific commands live in .dev_cycle/gates_config.sh.
# Run /init-dev-cycle to generate that file for your project.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Source project-specific gate commands
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/gates_config.sh"

if [[ ! -f "$CONFIG" ]]; then
  echo -e "${RED}Error: $CONFIG not found.${NC}"
  echo "Run /init-dev-cycle to generate project-specific gate configuration."
  exit 1
fi

source "$CONFIG"

gate_iteration() {
  echo "=== Iteration Gate ==="

  if should_run_codegen; then
    echo "Running codegen..."
    run_codegen || fail "Codegen failed"
    pass "Codegen clean"
  fi

  run_iteration_gate || fail "Iteration gate failed"
  pass "Gate checks clean"

  # Check for TODO/FIXME in recent changes
  TODOS=$(git diff --name-only HEAD~1 2>/dev/null | xargs grep -n 'TODO\|FIXME' 2>/dev/null || true)
  if [ -n "$TODOS" ]; then
    warn "TODOs in recently changed files — resolve before PR"
  fi

  echo -e "\n${GREEN}Iteration gate passed${NC}"
}

gate_pre_pr() {
  echo "=== Pre-PR Gate ==="

  if should_run_codegen; then
    echo "Running full codegen..."
    run_codegen || fail "Codegen failed"
    pass "Codegen clean"
  fi

  # Check for TODO/FIXME in changed files
  TODOS=$(git diff main...HEAD --name-only | xargs grep -n 'TODO\|FIXME' 2>/dev/null || true)
  if [ -n "$TODOS" ]; then
    warn "TODOs found in changed files:"
    echo "$TODOS"
  else
    pass "No TODOs in changed files"
  fi

  # Check for commented-out code blocks (heuristic)
  COMMENTED=$(git diff main...HEAD -U0 | grep '^+' | grep -c '^\+\s*//' || true)
  if [ "$COMMENTED" -gt 10 ]; then
    warn "Many comment lines added ($COMMENTED) — check for commented-out code"
  else
    pass "Comment density OK"
  fi

  run_pre_pr_gate || fail "Pre-PR gate failed"
  pass "Gate checks clean"

  echo -e "\n${GREEN}Pre-PR gate passed${NC}"
}

gate_final() {
  echo "=== Final Gate (post-merge verification) ==="

  run_final_gate || fail "Final gate failed"
  pass "Final gate passed"

  echo -e "\n${GREEN}Final gate passed${NC}"
}

case "${1:-iteration}" in
  iteration) gate_iteration ;;
  pre-pr) gate_pre_pr ;;
  final)  gate_final ;;
  *)
    echo "Usage: $0 [iteration|pre-pr|final]"
    echo "  iteration - Run after each implementation phase / slice"
    echo "  pre-pr    - Run before creating PR"
    echo "  final     - Run after merge (clean build verification)"
    exit 1
    ;;
esac
