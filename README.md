# Claude Second Brain

A safety-first workflow toolkit for [Claude Code](https://docs.anthropic.com/en/docs/claude-code): 27 slash commands + 17 agents that enforce predictable, auditable, quality-gated development — plus a local memory system that persists across sessions.

**Before anything else:** `/metaprompt` turns a vague ask into a structured execution plan a senior engineer would write. Here is what that looks like.

---

## What `/metaprompt` does (BEFORE/AFTER)

**BEFORE** — what you type without it:

```
/metaprompt I need a recap on what's built, what's not built, what we're
doing next, and suggestions for the next steps
```

**AFTER** — the structured prompt it produces:

```markdown
# Mission
Tight one-screen recap. Three sections, each ≤200 words: BUILT, NOT BUILT, NEXT.
Reader re-orients in <60 seconds.

# Phases
1. Comprehensive scan: active repos `git log --oneline -20`,
   checkpoint.md, TaskList, recent feedback memories, in-flight agents.
2. Classify: Built = landed+committed; Not Built = queued OR declined-with-reason;
   Next = user-priority → dependency → ship-cost-vs-value.
3. Deliver in exact format below.

# Format
## ✓ Built — [artifact, where it lives, why]
## ⏳ Not built / queued — [item, reason]
## ▶ Next (ranked) — [verb + concrete artifact + estimate + dependency]
**Recommend:** [single highest-leverage move, one-sentence rationale]

# Constraints
- ≤600 words. Trim "Built" first if over.
- ONE consolidated recap; no section-by-section pinging.
- Include 1 honest-decline if any framing was refused.
```

The AFTER adds a format, a word budget, priority-ranking criteria, and an honesty requirement. The BEFORE relies on Claude inferring all of that — and it usually doesn't. Five more real transformations: [docs/METAPROMPT-EXAMPLES.md](docs/METAPROMPT-EXAMPLES.md).

---

## Why this exists

Autonomous coding agents have documented failure modes: uncontrolled file operations, supply-chain attacks via malicious skills, agents acting on prompt injections without user gates, in-flight tasks lost when context compaction fires. The failure pattern is not the model — it is the absence of enforcement layers between a fuzzy instruction and an irreversible action.

This toolkit adds enforcement without infrastructure. Every safety property uses Claude Code primitives that already exist on your machine: CLAUDE.md rules, Python hooks, plan-mode reliance, and append-only log files. No binary, no Docker-per-session, no policy server, no pip dependency beyond the memory system's optional LM Studio backend.

---

## The 5 safety primitives shipped by default

**1. Plan-mode-first.** Non-trivial changes run through Claude Code's built-in plan mode. The model proposes; you approve; then it executes. Speculative edits require an explicit gate.
- Enforced via: CLAUDE.md template rule ("Plan first") + `/orchestrate` and `/team` approval prompts before Layer 1 executes.

**2. Append-only audit journal.** Every structural decision Claude makes during a session is written to `session_bridge.md` with an ISO-8601 timestamp. The file is append-only — no entry is ever rewritten or deleted.
- Enforced via: `memory-mcp/continuity_dump.py::append_bridge_entry()` — `fcntl.LOCK_EX` on append, 500-char payload cap, newline stripping to preserve one-entry-per-line invariant.

**3. Validation gates between agent dispatches.** In `/team` workflows, a `code-reviewer` and `verification-agent` run after implementation agents and before any commit. The pipeline does not advance unless the gate passes.
- Enforced via: layer-strict execution in `commands/team.md` (Phase 0.5 → 4) — Layer N+1 cannot start until Layer N returns.

**4. Privacy floor (metadata-only continuity).** At context compaction, the pre-compact snapshot reads `session_bridge.md` entries only — structured metadata Claude wrote, never `.jsonl` transcript bodies, never message content.
- Enforced via: `memory-mcp/continuity_dump.py` docstring contract ("NEVER reads transcript message bodies") + `_read_bridge_entries()` which opens only `bridge_path`, never `transcript_path`.

**5. Truthfulness rule (workflow norm).** Every novelty claim requires a verifiable code path or concrete comparison before shipping. No marketing-speak.
- Enforced via: `/metaprompt` structures fuzzy asks into phased, format-constrained prompts before any agent dispatches; `code-reviewer` and `verification-agent` validate diffs against checklist criteria before commit.

---

## Common agent-attack categories — coverage

Six of seven common agent-attack categories are addressed by existing primitives. The seventh (jailbreaking across models) is out of scope — this toolkit is single-model, Claude-only.

| Attack category | Defense (verifiable) |
|---|---|
| Prompt injection (direct / indirect / cross-agent) | Plan mode gates execution; `/metaprompt` structures fuzzy asks; privacy floor blocks injected content via memory |
| Tool abuse / privilege escalation | No-auto-push rule in CLAUDE.md; path-traversal guards in `bridge_append.py` + `precompact_hook.py::_resolve_memory_dir()` |
| Context/memory poisoning | Append-only bridge journal; confidence + visibility controls in `memory-mcp/db.py`; metadata-only continuity dump; truthfulness rule |
| Identity spoofing (agent-to-agent) | ISO-8601 timestamps on all bridge entries; single-orchestrator pattern — no direct agent-to-agent channel |
| Data exfiltration via side channels | Stop-hook safety (no stdout writes in hooks); 500-char payload cap in `continuity_dump.py::_MAX_PAYLOAD_LEN`; local-only `memory.db`; metadata-only writes |
| Trust boundary violations | Plan mode = explicit approval gate; bridge journal append-only = audit unevadable |
| Jailbreaking across models | Out of scope — single-model, Claude-only |

Categories drawn from common offensive-security taxonomies for AI agents (prompt injection, tool abuse, memory poisoning, identity spoofing, exfiltration, trust-boundary violations, jailbreaking).

---

## Where this fits in the ecosystem

Adjacent toolkits exist with different shapes:

- **[everything-claude-code](https://github.com/affaan-m/everything-claude-code)** (affaan-m, 169k stars) — comprehensive multi-platform agent harness (Claude Code, Codex, Opencode, Cursor). Ships an integrated agent-security scanner via the `/security-scan` skill — red-team / blue-team / auditor pipeline, 102 static rules, 1,282 tests, also available as standalone CLI / GitHub Action / GitHub App. Their posture: detect vulnerabilities in existing agent configs.

- **[claude-code-harness](https://github.com/Chachamaru127/claude-code-harness)** (Chachamaru127) — Go-native binary, R01-R13 declarative rules, Plan → Work → Review autonomy loop.

- **OpenClaw, Lovable, Bolt, Rork** — different categories (mass-deployed autonomous frameworks; hosted no-code UIs). Not direct comparisons for Claude Code config users.

This toolkit does less. Smaller surface (27 commands, 17 agents). What we ship:

- **Opinionated primitive defaults** that prevent classes of failure by design — append-only audit journal, plan-mode-first, privacy floor on continuity, truthfulness rule, validation gates between agents.
- **Code-level security scanning** at a different layer than agent-config scanners: `/scan` (full repo health: security + quality + gaps + ops), `/audit` (6-dimension codebase audit incl. security), `security-auditor` agent.

The agent-config layer (MCP servers, hooks, permission misconfigs, prompt-injection vectors) is well-served by scanners like the `/security-scan` skill in everything-claude-code. The code layer (vulnerabilities in your application code, missing tests, dependency CVEs) is what our scanners target. Complementary, not competing.

---

## What's included

This is a starter library. Agents are not a fixed catalog — `/orchestrate` and `/team` compose them dynamically per task using Claude Code's Agent tool. Your own agents go in `~/.claude/agents/` and are never touched by updates.

### Commands (27)

| Command | What it does |
|---------|-------------|
| `/status` | Instant progress report — git state, tests, next steps |
| `/explain` | 3-level code explainer with ASCII data flow diagrams |
| `/tdd` | Strict red-green-refactor TDD cycle |
| `/verify` | 7-step health check with traffic-light report |
| `/commit-push-pr` | Quality-gated commit, push, and PR workflow |
| `/document` | Generate or update docs — always shows diffs |
| `/new-project` | Scaffold a project with CLAUDE.md template |
| `/learn` | Capture learnings into CLAUDE.md |
| `/recall` | Search project knowledge (CLAUDE.md, docs, code) |
| `/audit` | Full 6-dimension codebase audit with scorecard |
| `/gap-analysis` | Find missing tests, docs, error handling, types |
| `/research` | Deep 3-track technical research with sources |
| `/orchestrate` | Multi-agent task decomposition and execution |
| `/metaprompt` | Upskill a fuzzy task into a phased, quality-gated, executable prompt |
| `/sync-memories` | Export/import knowledge between machines |
| `/guide` | Interactive toolkit assistant — suggests commands for your task |
| `/diagnose` | Interpret error screenshots, logs, or stack traces and fix |
| `/scan` | Full repository health scan — security, quality, gaps, operational health |
| `/flag` | Flag findings for team review instead of fixing unilaterally |
| `/resolve-pr` | Fetch PR review comments, fix code, reply politely, push |
| `/sync-skill-docs` | Sync new skills to the team toolkit repo with documentation updates |
| `/team` | Analyze project + assemble optimal agent team, execute in layers |
| `/harden-memory` | Audit and harden the memory auto-sync pipeline end-to-end |
| `/economy` | Optimize token consumption while maintaining result quality |
| `/context-save` | Checkpoint task state to survive context compaction |
| `/idea` | Capture a side-idea instantly without breaking current task flow |
| `/ideas` | View, prioritize, and manage the captured ideas backlog |

### Agents (17, starter library)

**Role-based (7):** `architect`, `tdd-agent`, `security-auditor`, `code-reviewer`, `documentation-agent`, `research-agent`, `verification-agent`

**Domain expert (10):** `senior-frontend-dev`, `senior-backend-dev`, `senior-fullstack-dev`, `senior-data-scientist`, `ml-engineer`, `devops-engineer`, `database-engineer`, `performance-engineer`, `sre-agent`, `qa-strategist`

Full reference: [docs/AGENTS.md](docs/AGENTS.md)

---

## Try it now

```bash
git clone <repo-url> claude-second-brain
cd claude-second-brain
./install.sh
```

Then in Claude Code:

```
/guide tour         # see what's available
/status             # where am I, what's in flight?
/tdd Add input validation to signup form
```

`/guide tour` lists every command with a one-line description. `/status` takes ~5 seconds and prevents working on stale state. `/tdd` enforces red-green-refactor — tests first, always.

Install sets up command symlinks, the memory-mcp venv, and the PreCompact git hook. The memory system itself requires [SETUP-MEMORY.md](SETUP-MEMORY.md) (optional LM Studio for semantic search; falls back to keyword-only without it). Set aside 5 minutes: [QUICK-START.md](QUICK-START.md).

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| **[QUICK-START.md](QUICK-START.md)** | Install guide + first 5-minute walkthrough + hands-on sandbox |
| **[TOOLKIT.md](TOOLKIT.md)** | 9 BEFORE/AFTER scenarios — the workflow difference in practice |
| **[PLAYBOOK.md](PLAYBOOK.md)** | Daily recipes, prompt patterns, agent composition, AI/LLM security |
| **[docs/TOP-COMMANDS.md](docs/TOP-COMMANDS.md)** | Top 10 commands cheat sheet with examples + decision tree |
| **[docs/COMMANDS.md](docs/COMMANDS.md)** | Full reference for all 27 commands |
| **[docs/AGENTS.md](docs/AGENTS.md)** | Full reference for all 17 agents |
| **[docs/ADVANCED-PATTERNS.md](docs/ADVANCED-PATTERNS.md)** | Skills crystallization, context recovery, post-audit remediation |
| **[docs/PURPOSE.md](docs/PURPOSE.md)** | Public/private boundary — what each subtree is and is not for |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues + Security & Portability env-var reference |
| **[SETUP-MEMORY.md](SETUP-MEMORY.md)** | Memory system installation — LM Studio, MCP server, hybrid search |
| **[CLAUDE.md.template](CLAUDE.md.template)** | Global rules template — TDD, security, self-learning protocol |
| **[docs/FIRST-10-MINUTES.md](docs/FIRST-10-MINUTES.md)** | Onboarding extension — carries the 5-minute tour to 10 minutes |
| **[docs/CONTINUITY-RESUME-DEMO.md](docs/CONTINUITY-RESUME-DEMO.md)** | Hands-on continuity demo — bridge journal, PreCompact snapshot, `/resume` |
| **[docs/OSS-ADOPTION-CHECKLIST.md](docs/OSS-ADOPTION-CHECKLIST.md)** | 7-question fit-check — should you use this toolkit? |
| **[examples/MEMORY-WALKTHROUGH.md](examples/MEMORY-WALKTHROUGH.md)** | Memory system walkthrough with real output |
| **[examples/RESOLVE-PR-WALKTHROUGH.md](examples/RESOLVE-PR-WALKTHROUGH.md)** | End-to-end PR resolution walkthrough |
| **[examples/sandbox/CONTRADICTIONS-DEMO.md](examples/sandbox/CONTRADICTIONS-DEMO.md)** | 90-second hands-on: contradiction detection + self-learning firing live |

---

## Contributing

Built a useful workflow? Add it:

1. Create a `.md` file in `commands/` or `agents/`
2. Include YAML frontmatter with `description:`
3. Write clear, phased instructions
4. Open a PR

Personal commands and agents go in `~/.claude/commands/` and `~/.claude/agents/` — never touched by toolkit updates.

## License

MIT
