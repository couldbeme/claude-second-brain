# Playbook: Practical Patterns for Claude Code

Recipes, prompt patterns, and agent composition strategies for common development tasks. This is a living document -- add your own patterns as you discover them.

**New to the toolkit?** Start with `/guide tour` for a quick overview, or `/guide [what you want to do]` to get a recommended workflow.

---

## Daily Workflow Patterns

### Start of Day

```
/status                         # see where things stand
/recall what I was working on   # reload context from yesterday
```

### Before Modifying Unfamiliar Code

```
/recall [module name]           # check for existing knowledge, gotchas
/explain src/module/            # understand architecture and flow
```

### End of Day

```
/learn from session             # capture discoveries before you forget
```

### Before Any PR

```
/verify                         # full health check
/commit-push-pr                 # quality-gated ship
```

---

## Task Recipes

### Adding a New API Endpoint

```
/recall existing endpoint patterns          # 1. Check existing conventions
/tdd Add GET /api/products                  # 2. Build with tests first
/document src/api/products.py               # 3. Generate docs
/verify                                     # 4. Health check
/commit-push-pr                             # 5. Ship it
```

### Onboarding to a New Codebase

```
/explain whole project                      # 1. Get the big picture
/audit                                      # 2. Understand health
/gap-analysis                               # 3. Find what's missing
# Read the CLAUDE.md, fill in gaps with:
/learn [discovery about the project]        # 4. Capture knowledge for next person
```

### Pre-Release Checklist

```
/verify full project                        # 1. Everything green?
/audit security                             # 2. Security scan
/gap-analysis                               # 3. Missing tests/docs/error handling?
/document README                            # 4. Docs up to date?
/commit-push-pr                             # 5. Ship with confidence
```

### Investigating a Bug

```
/recall [error message or symptom]          # 1. Was this seen before?
/explain src/affected-module/               # 2. Understand the area
/tdd Fix [the bug]                          # 3. Test-first fix
/learn [what caused it]                     # 4. Prevent recurrence
```

### Refactoring Safely

```
/recall [module] patterns                   # 1. Know existing conventions
/explain src/module/                        # 2. Understand dependencies
/gap-analysis src/module/                   # 3. Find test gaps FIRST
/tdd Add missing tests for src/module/      # 4. Cover untested paths
/tdd Refactor [specific change]             # 5. Now refactor with safety net
/verify                                     # 6. Confirm nothing broke
```

---

## Context-First Checklist

**Before starting ANY task, check existing knowledge.** This prevents duplicate work and builds on what's already been learned.

1. **Read CLAUDE.md** -- architecture, conventions, gotchas
2. **Run `/recall [task topic]`** -- previous sessions may have solved it
3. **Check recent audit/gap-analysis** -- findings may be relevant
4. **Review memory topics** -- `.claude/memory/` topic files
5. **Search existing code** -- a similar pattern might already exist

This is especially important when:
- Onboarding to a project a teammate has been working on
- Returning to a project after a break
- Starting a task that seems similar to something done before

---

## Agent Composition Strategies

### When to Use /orchestrate vs. Individual Commands

| Scenario | Use |
|----------|-----|
| Single concern (just tests, just docs, just security) | Specific command (`/tdd`, `/document`, `/audit`) |
| Multiple concerns (design + impl + tests + security) | `/orchestrate` |
| Research-heavy task | `/research` first, then `/orchestrate` with findings |
| Quick fix with tests | `/tdd` directly |
| Understanding before changing | `/explain` then `/tdd` |

### Effective /orchestrate Prompts

Include these in your orchestrate request for best results:

```
/orchestrate Add [feature] to the [module]
Constraints:
- Don't modify [existing thing]
- Must have 90%+ test coverage
- Handles [specific data type] -- security matters
- Follow existing patterns in src/[similar module]/
```

### Agent Capabilities Quick Reference

| Need | Agent | What it does |
|------|-------|-------------|
| "How should I build this?" | architect | Blueprint with file paths, interfaces, build sequence |
| "Implement with tests" | tdd-agent | Strict red-green-refactor cycles |
| "Is this secure?" | security-auditor | OWASP + LLM security scan with severity ratings |
| "Review my changes" | code-reviewer | Bug detection with confidence scores (>=75 only) |
| "Write the docs" | documentation-agent | Accurate docs as diffs, matching project style |
| "Research this topic" | research-agent | Multi-source investigation with citations |
| "Does everything work?" | verification-agent | Sequential test/lint/build pipeline |

---

## Prompt Patterns That Work Well

### The Constraint Pattern

Tell Claude what NOT to do. Constraints prevent common mistakes.

```
/tdd Add rate limiting to /api/users
Constraints:
- Use Redis (not in-memory) -- we run multiple replicas
- Max 100 requests per minute per API key
- Return 429 with Retry-After header
- Must not break existing tests
```

### The Context-First Pattern

Load knowledge before giving instructions.

```
/recall authentication patterns
[read the results]

/tdd Refactor auth middleware to support JWT refresh tokens
Context: We use [specific pattern from /recall], tokens stored in [location]
```

### The Iterative Refinement Pattern

Start with `/metaprompt`, then refine before executing.

```
/metaprompt Add a caching layer to the user service

[review generated prompt]
"Add a constraint: cache invalidation must happen on user update"
[review refined prompt]
"Use immediately"
```

### The Scope-Bounded Pattern

Be specific about what to touch and what to leave alone.

```
/orchestrate Add email notifications for order status changes
Scope:
- Only modify src/notifications/ and src/orders/events.py
- Do NOT touch src/orders/processing.py (critical path, fragile)
- Use the existing EventBus pattern in src/events/bus.py
```

---

## AI/LLM Security Patterns

### Auditing an AI-Powered Application

```
/audit security

# Then specifically check AI-related risks:
# - Prompt injection in src/ai/ (user input → LLM prompts)
# - Agent permissions in .claude/agents/ (least privilege)
# - Memory DB for stored secrets (accidental PII in embeddings)
# - Model API authentication (is localhost:1234 exposed?)
```

### Secure Prompt Construction

**Bad** -- user input in system prompt:
```python
prompt = f"You are a helper. Query: {user_input}"
```

**Good** -- structured message format:
```python
messages = [
    {"role": "system", "content": "You are a helper."},
    {"role": "user", "content": user_input},
]
```

### Agent Security Checklist

- Always specify `tools:` in agent definitions (deny by default)
- Use the most appropriate model for each agent's sensitivity level
- Review MCP server permissions in settings.json
- Never pass raw user input into LLM prompts without sanitization
- Check memory DB contents periodically for accidentally stored secrets

### Red Team Thinking

When reviewing AI-integrated code, ask:
- What happens if a user sends "ignore all previous instructions"?
- Can data from external sources (APIs, DB, files) influence prompt behavior?
- Are agent tool permissions minimal? Could a compromised agent do damage?
- Is the embedding service authenticated? Could it be poisoned?

---

## Memory System Patterns

### Effective /learn Usage

- One concept per learning (dense, not verbose)
- Include the WHY, not just the WHAT
- Tag with project name for project-specific learnings
- Use importance 8-10 for rules, 5-7 for patterns, 1-4 for temporary notes

```
# Good:
/learn Redis required for caching -- we run 4 replicas with no shared memory

# Too vague:
/learn use Redis for caching
```

### Keeping Memory Clean

```
/sync-memories stats              # check for stale entries
```

Review exported JSON periodically. Delete outdated memories that no longer apply.

### Cross-Session Continuity

Before long tasks, save context explicitly:

```
"Save to memory: working on JWT refactor, decided on async adapter
 pattern, completed middleware, next is webhook integration"
```

If context gets compressed mid-session, Claude auto-recovers via `memory_context`. If something seems off, run `/recall [current task]` manually.
