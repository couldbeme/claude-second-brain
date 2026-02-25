# Advanced Patterns

Deep dives into the toolkit's most powerful capabilities -- skills crystallization, context recovery, and post-audit remediation.

---

## Skills Crystallization: From Repetition to Reusable Commands

**The problem:** You find yourself doing the same multi-step workflow over and over. These workflows live in your head -- invisible, undocumented, and lost when you switch teams.

**How it works:** Claude detects repeated patterns and suggests turning them into slash commands via `/metaprompt`.

```
Session 12:
You:    "Add a GET /api/orders endpoint"
Claude: [writes route, handler, schema, test, docs -- same pattern as last 3 endpoints]

        I've noticed you follow the same workflow every time you add an endpoint:
        1. Create route in routes/
        2. Add Pydantic schema in schemas/
        3. Write handler with DB query
        4. Add tests (happy path + 404 + validation)
        5. Update API docs

        Want me to crystallize this into a /new-endpoint command?

You:    "Yes"
Claude: /metaprompt Create a slash command called /new-endpoint that...

        Generated: commands/new-endpoint.md

Session 13:
You:    /new-endpoint products GET,POST,DELETE
Claude: [follows the crystallized workflow perfectly, in seconds]
```

**The five steps:**
1. **Detection** -- The self-learning system tracks workflow patterns across sessions
2. **Suggestion** -- After 3+ repetitions, Claude proposes crystallization
3. **Generation** -- `/metaprompt` creates an optimized slash command
4. **Review** -- You refine it before saving (human in the loop)
5. **Propagation** -- PR the new command to the team toolkit repo so everyone benefits

Every team has 10-20 invisible workflows that take 15 minutes each. Crystallizing them into commands means 15 minutes becomes 15 seconds.

---

## Context Recovery: Never Lose Context

**The problem:** Long Claude Code sessions hit the context window limit. When this happens, Claude compresses earlier messages. Suddenly, Claude forgets what you were working on.

**How the toolkit solves it:**

```
Long session, 2 hours in:
[context compaction happens]

Without toolkit:
Claude: "I seem to have lost context. What were we working on?"
You:    [spends 10 minutes re-explaining everything]

With toolkit:
Claude: [detects context loss]
        [calls memory_context("current task context")]
        [reloads: task description, decisions made, approaches tried, learnings]

        "Context recovered from memory. We were implementing the rate limiter.
         We decided on Redis (not in-memory) because of multi-replica setup.
         Last completed: the middleware. Next: webhook integration.
         Continuing from where we left off."
```

**Three recovery layers:**

1. **Proactive saving** -- Before long operations, Claude saves task context to memory automatically
2. **Automatic recovery** -- When Claude detects context loss, it reloads from memory
3. **Manual fallback** -- Use `/recall` to search for specific context

The average complex session is 2-4 hours. Without recovery, you hit a wall at ~90 minutes. With memory, sessions can run indefinitely.

---

## Post-Audit Remediation: `/audit` + `/scan` + `/tdd`

**The problem:** `/audit` and `/scan` tell you what's wrong. But knowing isn't fixing. The scorecard sits there, findings accumulate.

**The workflow:** After the audit scorecard, use `/tdd` and `/orchestrate` to systematically address findings -- safely, with tests, and without breaking anything.

```
/scan

Phase 1: SCAN
══════════════
| Dimension   | Score | Top Issue |
|-------------|-------|-----------|
| Security    | 4/10  | SQL injection in search_users() |
| Tests       | 6/10  | Payment webhook: 0 test coverage |
| Quality     | 7/10  | 3 functions over 200 lines |
| Docs        | 5/10  | README install steps outdated |
| Performance | 8/10  | N+1 query in /api/users/list |

14 findings total. 3 critical, 4 high, 5 medium, 2 low.

Want me to start on item 1? → Yes

/tdd Fix SQL injection in search_users()

RED:   test_search_users_sql_injection() -- verifies parameterized query
GREEN: Replaced f-strings with parameterized queries (3 locations)
Tests: 50/50 passing

/tdd Add payment webhook tests

RED:   4 failing tests (success, failure, duplicate, invalid signature)
GREEN: All 4 passing
Tests: 54/54 passing

/verify
Overall: HEALTHY

/scan
Before: 14 findings, 3 critical, overall 6/10
After:  8 findings, 0 critical, overall 8.2/10
```

**The phases:**

| Phase | What happens | Commands |
|-------|-------------|----------|
| **Scan** | Full health check | `/scan` or `/audit` |
| **Triage** | Pick highest-impact items | Review the prioritized action list |
| **Fix** | TDD-first fixes | `/tdd Fix [finding]` |
| **Verify** | Confirm no regressions | `/verify` |
| **Learn** | Save findings to memory | `/learn from session` |

**Safety rails:**
- **TDD for every fix** -- No fix goes in without a failing test first
- **Verify after each batch** -- Run `/verify` to catch regressions
- **Before/after scorecard** -- Re-run `/scan` to see quantified improvement
- **Knowledge capture** -- Each fix becomes a learning that prevents recurrence
