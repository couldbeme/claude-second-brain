#!/usr/bin/env bash
# uninstall.sh — Remove toolkit symlinks from ~/.claude/
#
# Only removes symlinks that point into the toolkit repo.
# Personal files, memory database, settings, and CLAUDE.md are preserved.

set -euo pipefail

TOOLKIT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[0;90m'
RESET='\033[0m'

REMOVED=0
PRESERVED=0

echo ""
printf "${CYAN}Claude Second Brain Uninstaller${RESET}\n"
echo "======================================"
echo "Removing symlinks pointing to: $TOOLKIT_DIR"
echo "Preserving: personal files, memory.db, settings.json, CLAUDE.md"
echo ""

# Remove symlinks from agents/ and commands/
for dir in agents commands; do
    target_dir="$CLAUDE_DIR/$dir"
    [[ -d "$target_dir" ]] || continue

    printf "${CYAN}--- ${dir}/ ---${RESET}\n"
    for f in "$target_dir"/*.md; do
        [[ -e "$f" ]] || continue
        name="$(basename "$f")"

        if [[ -L "$f" ]]; then
            link_target="$(readlink "$f")"
            if [[ "$link_target" == "$TOOLKIT_DIR"/* ]]; then
                rm "$f"
                printf "  ${DIM}Removed:${RESET}   %s\n" "$name"
                ((REMOVED++))
            else
                printf "  ${YELLOW}Kept:${RESET}     %s (symlink to elsewhere)\n" "$name"
                ((PRESERVED++))
            fi
        else
            printf "  ${GREEN}Preserved:${RESET} %s (personal file)\n" "$name"
            ((PRESERVED++))
        fi
    done
done

# Remove memory-mcp symlinks
printf "${CYAN}--- memory-mcp/ ---${RESET}\n"
for f in "$CLAUDE_DIR/memory-mcp"/*.py "$CLAUDE_DIR/memory-mcp"/requirements.txt; do
    [[ -e "$f" ]] || [[ -L "$f" ]] || continue
    name="$(basename "$f")"

    if [[ -L "$f" ]]; then
        link_target="$(readlink "$f")"
        if [[ "$link_target" == "$TOOLKIT_DIR"/* ]]; then
            rm "$f"
            printf "  ${DIM}Removed:${RESET}   %s\n" "$name"
            ((REMOVED++))
        fi
    fi
done

# Remove post-merge hook (only the toolkit section)
hook_file="$TOOLKIT_DIR/.git/hooks/post-merge"
if [[ -f "$hook_file" ]] && grep -q "toolkit-auto-sync" "$hook_file" 2>/dev/null; then
    # If the hook only contains toolkit section, remove entirely
    non_toolkit_lines=$(grep -v -c "toolkit-auto-sync\|TOOLKIT_DIR\|install\.sh\|Auto-syncing\|end toolkit" "$hook_file" 2>/dev/null || echo "0")
    if [[ "$non_toolkit_lines" -le 2 ]]; then
        rm "$hook_file"
        printf "  ${DIM}Removed:${RESET}   post-merge hook\n"
    else
        printf "  ${YELLOW}Kept:${RESET}     post-merge hook (has non-toolkit content — edit manually)\n"
    fi
fi

echo ""
printf "${GREEN}Done.${RESET} Removed: $REMOVED  Preserved: $PRESERVED\n"
echo ""
echo "Preserved:"
echo "  ~/.claude/memory/memory.db  (your memories)"
echo "  ~/.claude/settings.json     (your config)"
echo "  ~/.claude/CLAUDE.md         (your rules)"
echo "  ~/.claude/memory-mcp/.venv/ (Python venv)"
[[ $PRESERVED -gt 0 ]] && echo "  + $PRESERVED personal agent/command files"
