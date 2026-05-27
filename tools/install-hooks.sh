#!/usr/bin/env bash
# One-time per-developer hook installer.
#
# Wires .githooks/ into git via `core.hooksPath` so the tracked hooks fire
# locally. Safe to re-run.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-push

echo "auto-docs: hooks installed."
echo "  core.hooksPath = $(git config --get core.hooksPath)"
echo "  pre-push       = .githooks/pre-push"
echo ""
echo "Disable for one push:    git push --no-verify"
echo "Disable for one commit:  include '[skip auto-docs]' in the subject"
echo "Uninstall:               git config --unset core.hooksPath"
