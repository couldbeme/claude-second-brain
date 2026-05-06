---
description: Optimize token consumption while maintaining result quality — applies economy rules to the current session
argument-hint: [optional: task to execute economically] (e.g., "Fix the auth bug" or just "on" to enable economy mode)
---

# Economy Mode

Optimize token usage for the current task without sacrificing result quality.

## Input

Task or mode: $ARGUMENTS

If $ARGUMENTS is "on", "enable", or "status", manage economy mode. Otherwise, execute the given task with economy rules applied.

## Economy Rules (apply immediately)

### 1. Search Before Read

**Never** read an entire file without first confirming it's relevant.

```
BAD:  Read all 500 lines of server.py to find the auth function
GOOD: Grep for "def authenticate" → found at line 42 → Read lines 38-55
```

- Use Glob to find files by pattern first
- Use Grep to locate the exact lines
- Read only the targeted range (offset + limit)
- For files > 200 lines, always use offset/limit

### 2. Batch Tool Calls

Every message costs tokens. Combine independent operations into a single response.

```
BAD:  Call Glob... wait... Call Grep... wait... Call Read... wait...
GOOD: Call Glob + Grep + Read in parallel (if independent)
```

- Launch independent searches in parallel (single message, multiple tool calls)
- Chain dependent calls sequentially (use && in Bash)
- Never make a tool call to check something you already know from context

### 3. Model Selection for Agents

Use the lightest model that can handle the job:

| Task | Model | Why |
|------|-------|-----|
| File search, pattern matching, simple edits | haiku | Fast, cheap, sufficient |
| Code review, implementation, architecture | sonnet | Good balance |
| Novel design, complex reasoning, ambiguous tasks | opus | Full capability |

When spawning subagents via Agent tool, set `model: "haiku"` for exploration/search tasks.

### 4. Avoid Re-Reading

Track what's already in context:

- If a file was read earlier in this conversation, don't read it again unless it changed
- If a search returned results, reference them — don't re-search
- If the user provided information, use it — don't verify what they told you

### 5. Compress Output

- Lead with the answer, then explain
- Use tables over paragraphs for comparisons
- Use bullet points over prose for lists
- Skip preamble ("Let me...", "I'll now...")
- Don't repeat the question back

### 6. Smart Context Management

- For large codebases: read CLAUDE.md and README first (project map), then targeted searches
- For multi-file changes: read only the sections you'll modify, not entire files
- For test files: read the specific test function, not the whole test suite
- Before long operations: summarize current state to avoid context re-read on compression

### 7. Minimize Subagent Count

- Don't spawn an agent for something you can do in one tool call
- Prefer 2-3 focused agents over 5+ overlapping agents
- Use `/tdd` directly instead of `/team` for single-concern tasks
- Use `/orchestrate` with 3 agents instead of `/team` with 7 if you know the scope

## Economy Report

After completing any task in economy mode, append a brief cost summary:

```
ECONOMY REPORT
==============
Tool calls:    12 (6 parallel batches)
Files read:    4 (targeted ranges, not full files)
Agents used:   2 (haiku for search, sonnet for implementation)
Lines read:    ~180 (vs ~2400 if full files)
Estimated savings: ~90% fewer input tokens vs naive approach
```

## Modes

### Enable for session
```
/economy on
```
Prints the economy rules as a reminder and applies them for the rest of the session.

### Execute task economically
```
/economy Fix the token validation bug in auth.py
```
Executes the task with all economy rules applied, then prints the economy report.

### Check current efficiency
```
/economy status
```
Reviews the current session's tool usage and suggests optimizations.

## Rules

1. **Quality floor is non-negotiable.** Economy mode reduces waste, not quality. Tests still pass. Security still checked. TDD still enforced.
2. **Targeted reads over full reads.** Always use offset + limit for files > 200 lines.
3. **Parallel over sequential.** Batch independent tool calls in a single message.
4. **Haiku for search, sonnet for code.** Match model to task complexity.
5. **Don't re-read, don't re-search.** Track what's already in context.
6. **Shortest correct answer wins.** Lead with the result, explain only if needed.
