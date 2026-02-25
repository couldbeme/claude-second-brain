---
description: Generate an optimized prompt/command for a specific task
argument-hint: Describe the task you want a prompt for
---

# Metaprompt Generator

Generate a highly effective prompt for the given task, optimized for Claude Code's capabilities.

## Input

Task: $ARGUMENTS

## Process

1. **Analyze the task**:
   - What is the desired outcome?
   - What tools will be needed? (Bash, Read, Edit, Glob, Grep, subagents)
   - What information does the prompt need to provide?
   - What could go wrong?

2. **Apply prompt engineering principles**:
   - Clear role definition
   - Explicit constraints and success criteria
   - Step-by-step structure with phases
   - Error handling instructions
   - Output format specification
   - Token efficiency (avoid unnecessary verbosity)

3. **Generate the prompt** in Claude Code slash command format:

   ```markdown
   ---
   description: [one-line description]
   argument-hint: [what user provides]
   ---

   [Full prompt content with phases, rules, and output format]
   ```

4. **Self-review**: Check the generated prompt for:
   - Ambiguity (could it be misinterpreted?)
   - Missing edge cases
   - Tool availability (does it reference tools Claude Code has?)
   - Token efficiency (is it unnecessarily verbose?)

5. **Present the prompt** and ask if the user wants to:
   - Use it immediately as instructions
   - Save it as a slash command (project or global)
   - Iterate on it
