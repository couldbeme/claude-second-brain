# Contradictions + Self-Learning — Hands-On Demo

This 90-second walkthrough shows two of the toolkit's most novel pieces firing live:

1. **The contradictions table** — when two memories contradict, the database writes a row naming both. Not at query time — at *write* time, in the same transaction. No LLM call. No threshold tuning.
2. **Self-learning Layer 1/2/3** — explicit corrections become durable feedback memories that catch the same slip next session.

Both are deterministic, both are auditable, both are five lines of SQL away from your terminal.

## Setup

You need the toolkit installed and a Python REPL in `memory-mcp/`:

```bash
cd ~/Dev/claude-second-brain/memory-mcp
python3
```

## Demo 1 — Contradictions firing

```python
from db import MemoryDB
from hybrid_search import hybrid_search

db = MemoryDB("/tmp/contradictions-demo.db")

# Session 1: agent records a high-confidence belief
id_a = db.save(
    content="The rate-limiter is always enabled in production",
    category="context",
    project="api-gateway",
    tags=["rate-limiter", "production"],
    confidence=0.95,
)

# Session 2 (could be next week): contradicting belief, lower confidence
id_b = db.save(
    content="The rate-limiter is never enabled in production",
    category="context",
    project="api-gateway",
    tags=["rate-limiter", "production"],
    confidence=0.30,
)

print(db.get_contradictions(id_b))
# → ['<id_a>']
```

The contradiction was detected at the moment of the second `save()` — not later, not when queried, not by an LLM judge. The keyword-inversion pair `("always", "never")` is in a hardcoded lookup at `db.py:502-512`. The detection runs in the same transaction as the write at `db.py:525-606`.

Now look at it directly:

```python
import json
rows = db.conn.execute(
    "SELECT id, memory_a_id, memory_b_id, detected_at, resolution FROM contradictions"
).fetchall()
print(json.dumps(rows, default=str, indent=2))
```

```json
[
  ["<contra-id>", "<id_a>", "<id_b>", "2026-04-29 ...", "unresolved"]
]
```

This row didn't exist 30 seconds ago. It was written automatically. It is `unresolved` until something or someone explicitly closes it. A monitoring system can poll:

```sql
SELECT COUNT(*) FROM contradictions WHERE resolution = 'unresolved';
```

That count is your drift alarm. No third-party service required.

## Demo 2 — Confidence affects retrieval

Two memories with identical text — only the confidence differs:

```python
id_high = db.save(
    content="rate-limiter config is controlled via feature flag",
    category="context", project="api-gateway",
    tags=["rate-limiter"], importance=5, confidence=0.95,
)
id_low = db.save(
    content="rate-limiter config is controlled via feature flag",
    category="context", project="api-gateway",
    tags=["rate-limiter"], importance=5, confidence=0.30,
)

results = hybrid_search(db, "rate-limiter feature flag", None, project="api-gateway")
for r in results[:4]:
    print(f"  conf={r['confidence']}  score={r['score']}  id={r['id'][:8]}")
```

```
  conf=0.95  score=0.XXXX  id=<high prefix>
  conf=0.30  score=0.XXXX  id=<low prefix>
```

`hybrid_search.py:84-85` multiplies the combined BM25 + vector score by confidence at rank time. Identical text, identical importance, identical text similarity — the 0.95-confidence belief ranks first. The 0.30-confidence belief, the one the agent flagged as tentative when saving, cannot leapfrog a confident one purely on textual relevance.

## Demo 3 — Self-learning Layer 1 (explicit correction)

Open Claude Code in this `examples/sandbox/` directory. Paste:

```
There's a bare except in search_users that's swallowing errors. We
should never use bare excepts in this project — always catch specific
exceptions and log the rest. Add this as a project-level learning
before fixing.
```

Watch what happens:

1. Claude tags the correction `[LEARNING]` inline.
2. It writes the rule to `~/.claude/projects/<slug>/memory/feedback_no_bare_except.md` (or similar) with `Why:` and `How to apply:` lines.
3. It updates `MEMORY.md` to index the new feedback memory.
4. **Next session, when you start writing exception-handling code, that feedback memory is auto-loaded into context.** Claude will catch the next bare-except attempt before you do.

Layer 1 is the explicit-correction layer. Layer 2 catches *inferred* corrections (rhetorical questions, past-behavior references). Layer 3 silently observes communication style, decision-making preferences, and frustration signals to adapt without ever surfacing the observation. See `~/.claude/CLAUDE.md` self-learning protocol for the full layer definitions.

## What just happened

In about three minutes you saw:

- A contradictions table firing **at write time**, no LLM call.
- Save-time confidence **propagating into retrieval ranking**.
- An explicit correction becoming a **durable cross-session learning**.

Together: a memory layer that monitors its own consistency, weights its own beliefs, and remembers the corrections it received. None of this is a wrapper around someone else's API. It is a SQLite file on your filesystem.

## Where to read the code

| Concern | File:lines |
|---|---|
| Contradictions table schema | `memory-mcp/db.py:99-109` |
| Inversion-pair lookup | `memory-mcp/db.py:502-512` |
| Detection logic (write-time) | `memory-mcp/db.py:525-606` |
| Confidence multiplier in retrieval | `memory-mcp/hybrid_search.py:84-85` |
| Save-time confidence clamp | `memory-mcp/db.py:165` |
| Self-learning Layers 1/2/3 protocol | `~/.claude/CLAUDE.md` (loaded each session) |

## What this is NOT

- Not a prompt-engineering trick — the contradiction detection is pure SQL on tag-overlap windows. No LLM in the loop.
- Not a benchmark claim — it's a write-time event surface. Performance is measured separately by Coherence Yield (see `docs/efficacy/`).
- Not magic — the inversion-pair list is nine pairs. Semantic contradiction (no shared antonym) is documented as v0.2 work, not silently missing.

## Try breaking it

The most informative way to learn the system's edges is to find what it doesn't catch:

```python
# This SHOULD contradict but won't (no shared antonym pair)
db.save(content="The rate-limiter applies to authenticated users only",
        category="context", project="api-gateway", tags=["rate-limiter"])
db.save(content="The rate-limiter applies to all users including anonymous",
        category="context", project="api-gateway", tags=["rate-limiter"])
print(db.get_contradictions(...))   # likely empty — semantic miss
```

That's the v0.2 boundary. File an issue if you find one we should add to the inversion-pair table.
