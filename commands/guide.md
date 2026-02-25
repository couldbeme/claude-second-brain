---
description: Interactive toolkit assistant — suggests commands, workflows, and agents for your task
argument-hint: What are you trying to do? (or "tour" for a quick walkthrough)
---

# Guide -- Toolkit Assistant

Help the user figure out which commands, agents, and workflows to use for their current task. Act as a concierge for the toolkit — especially useful for new teammates.

## Input

Goal: $ARGUMENTS

## Phase 1: Understand Intent

If the user said "tour", skip to the **Tour** section below.

Otherwise, classify the user's goal into one or more of these categories:

| Category | Signals |
|----------|---------|
| **Orient** | "new here", "understand", "onboard", "what does this do", "where is", "explain" |
| **Build** | "add", "implement", "create", "feature", "endpoint", "refactor", "fix", "bug" |
| **Analyze** | "audit", "security", "review", "gaps", "missing", "coverage", "performance" |
| **Ship** | "commit", "PR", "push", "release", "deploy", "merge" |
| **Research** | "how to", "best practice", "compare", "evaluate", "should I use" |
| **Knowledge** | "remember", "learned", "recall", "what did we", "sync", "export" |
| **Meta** | "optimize prompt", "create command", "workflow for" |

If the goal is ambiguous, ask ONE clarifying question before proceeding.

## Phase 2: Recommend Workflow

Based on the category, suggest a specific workflow. Always explain WHY each step matters.

### Orient scenarios

**"I'm new to this codebase"**
```
1. /explain whole project          — get the big picture first
2. /audit                          — understand health and risks
3. /gap-analysis                   — see what's missing
4. /learn [your discoveries]       — save knowledge for the next person
```
Why: You can't build well on a codebase you don't understand. This sequence gives you architecture → health → gaps → captured knowledge in ~15 minutes.

**"I need to understand this module before changing it"**
```
1. /recall [module name]           — check if others have documented it
2. /explain src/module/            — understand architecture and flow
```
Why: `/recall` first prevents you from re-learning what a teammate already discovered. `/explain` gives you the three-level breakdown (high/medium/detail).

---

### Build scenarios

**"Add a new feature / API endpoint"**
```
1. /recall [similar feature]       — check existing patterns
2. /tdd [feature description]      — build with tests first
3. /document [what you built]      — generate docs
4. /verify                         — full health check
5. /commit-push-pr                 — ship it
```
Why: Context first (don't reinvent), TDD for safety, docs for teammates, verify before shipping.

**"Fix a bug"**
```
1. /recall [error message]         — was this seen before?
2. /explain [affected module]      — understand the area
3. /tdd Fix [the bug]              — test-first fix
4. /learn [root cause]             — prevent recurrence
```
Why: The most common mistake is jumping straight to fixing. Checking history and understanding context first means you fix the root cause, not just the symptom.

**"Refactor safely"**
```
1. /recall [module] patterns       — know existing conventions
2. /explain src/module/            — understand dependencies
3. /gap-analysis src/module/       — find test gaps FIRST
4. /tdd Add missing tests          — cover untested paths
5. /tdd Refactor [specific change] — now refactor with safety net
6. /verify                         — confirm nothing broke
```
Why: Refactoring without test coverage is gambling. Steps 3-4 build the safety net BEFORE you start changing things.

**"Complex task (multiple concerns)"**
```
/orchestrate [full task description]
```
Why: When a task needs architecture + implementation + security + docs, `/orchestrate` decomposes it and dispatches specialized agents in parallel. Much faster than running each command sequentially.

---

### Analyze scenarios

**"Is this codebase secure?"**
```
1. /audit security                 — full 6-dimension audit (includes AI/LLM risks)
2. /gap-analysis                   — find missing error handling, validation
```
Why: `/audit` covers OWASP top 10, dependency vulnerabilities, AND AI-specific risks (prompt injection, agent safety, data poisoning). `/gap-analysis` catches what the security-specific scan might miss.

**"What's the quality of this code?"**
```
/audit                             — full 6-dimension audit with scorecard
```
Why: One command gives you security, test coverage, code quality, documentation, performance, and AI/LLM security scores. The scorecard tells you exactly where to focus improvement effort.

**"What's missing?"**
```
/gap-analysis [optional scope]     — tests, docs, error handling, types
```
Why: Systematically finds holes. Especially useful before refactoring (to know what test coverage to add first) or before release (to catch gaps).

---

### Ship scenarios

**"Ready to ship"**
```
1. /verify                         — full health check (tests, lint, build)
2. /commit-push-pr                 — quality-gated commit + PR
```
Why: `/verify` catches broken tests, lint errors, and build failures BEFORE you commit. `/commit-push-pr` runs its own checks too, but `/verify` gives you the detailed report first.

**"Pre-release checklist"**
```
1. /verify full project
2. /audit security
3. /gap-analysis
4. /document README
5. /commit-push-pr
```
Why: The full pipeline: everything green → security hardened → no gaps → docs current → shipped.

---

### Research scenarios

**"How should I approach this?"**
```
/research [topic or question]
```
Why: Runs 3 parallel research tracks (web search, codebase analysis, documentation review) and synthesizes findings with citations. Use this BEFORE building when the approach isn't clear.

**"I need an expert prompt for a complex task"**
```
/metaprompt [describe your task]
```
Why: Transforms a basic prompt into an agent-optimized prompt with phases, constraints, tool mapping, and error handling. The difference between "add auth" and a 5-phase engineered prompt that agents execute flawlessly.

---

### Knowledge scenarios

**"Save what I learned"**
```
/learn [what you discovered]       — or "/learn from session" to extract all
```

**"What do we know about X?"**
```
/recall [topic]
```

**"Sync knowledge to another machine"**
```
/sync-memories export              — export to JSON (git-committable)
/sync-memories import              — import on another machine
```

---

## Phase 3: Suggest Next Steps

After recommending a workflow:

1. **Ask if they want to start** — "Want me to run the first command now?"
2. **Offer alternatives** — if there's a simpler or more advanced approach, mention it
3. **Flag prerequisites** — if a command needs the memory system, LM Studio, or `gh` CLI, say so

## Tour

If the user asked for a tour, give them this quick overview:

```
Welcome to the Claude Code Team Toolkit! Here's what you have:

ORIENT — understand before you build
  /status          Where am I? What's in flight?
  /explain         How does this code work? (3-level breakdown)
  /recall          What do we already know about this?

BUILD — write code the right way
  /tdd             Test-first development (red → green → refactor)
  /verify          Full health check (tests, lint, build)
  /commit-push-pr  Quality-gated shipping

ANALYZE — find problems before they find you
  /audit           6-dimension codebase audit with scorecard
  /gap-analysis    Find missing tests, docs, error handling

RESEARCH & LEARN
  /research        Deep 3-track investigation with sources
  /learn           Save discoveries for the team
  /recall          Search project knowledge
  /sync-memories   Export/import knowledge between machines

POWER TOOLS
  /orchestrate     Multi-agent team for complex tasks
  /metaprompt      Generate agent-optimized prompts
  /document        Generate or update documentation
  /new-project     Scaffold a new project with standards

/guide [what you want to do]  — run this anytime for workflow advice
```

**Pro tip**: Always start with `/recall [your task]` before building anything. Previous sessions may have already solved your problem.
