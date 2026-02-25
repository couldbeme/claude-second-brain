---
description: Search project knowledge for relevant context
argument-hint: What to search for
---

# Recall -- Search Project Knowledge

Search across all project knowledge sources for relevant information.

## Input

Query: $ARGUMENTS

## Process

1. **Search CLAUDE.md files**:
   - `.claude/CLAUDE.md` (current project)
   - `~/.claude/CLAUDE.md` (global, if exists)

2. **Search project documentation**:
   - README.md
   - docs/ directory (if exists)
   - Inline comments and docstrings in relevant files

3. **Search for patterns in code**:
   - Use Grep to find references to the query topic in source files
   - Check test files for usage examples

4. **Synthesize results**:
   ```
   ## Recall Results: [query]

   ### From Project CLAUDE.md
   [relevant excerpts]

   ### From Global CLAUDE.md
   [relevant excerpts]

   ### From Documentation
   [relevant excerpts]

   ### From Code
   [relevant file references and patterns]

   ### Related Files
   - [file1] -- [relevance]
   - [file2] -- [relevance]
   ```

5. If nothing found: "No existing knowledge found for this topic. Try broadening the search or checking with the team."
