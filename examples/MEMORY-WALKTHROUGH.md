# Memory System — Hands-On Walkthrough

## Why memory matters

Without persistent memory, every Claude Code session starts cold. You
re-explain the caching strategy, re-describe the retry pattern, re-correct
the mistake Claude made three sessions ago. The context window fills with
re-orientation instead of work. The memory system stores what Claude learns
about your project — decisions, patterns, corrections — in a local SQLite
database with hybrid search (semantic vector + BM25 keyword). The next
session starts with that knowledge loaded, not re-stated.

Concrete pain it solves: Claude used an in-memory dict for caching in
session 3. You corrected it — Redis, multi-replica setup, not per-process.
In session 4, without memory, you correct it again. With memory, that
correction is a durable entry ranked first when Claude looks up caching. It
won't make that mistake again.

---

## Pre-flight

Complete [SETUP-MEMORY.md](../SETUP-MEMORY.md) Steps 1–5 before this
walkthrough. Verify with:

```bash
python <your-toolkit-path>/memory-mcp/server.py --health-check
# Memory MCP server OK
```

LM Studio running is recommended (semantic search). Without it, the system
still works with keyword-only search.

---

## Day 1 — Capture a learning with `/learn`

Open Claude Code in your project. You've just discovered something
non-obvious about how the codebase handles authentication.

```
/learn The refresh token endpoint accepts expired access tokens as proof of
       identity — this is intentional. It's documented in docs/auth-flow.md
       but easy to miss. Don't add a validation check that rejects expired
       tokens here.
```

What happens inside:

1. Claude tags it `[LEARNING]` inline.
2. It calls `memory_save` with:
   - `content`: the learning text
   - `category`: `"context"` (project-specific knowledge)
   - `tags`: inferred from content (`["auth", "refresh-token", "intentional-design"]`)
   - `importance`: set based on signal strength (this one: 8, because of "don't")
   - `confidence`: 0.9 (high — explicit correction from user)
3. LM Studio generates a 768-dim embedding of the content.
4. The entry lands in three places simultaneously:
   - `memories` table (content + metadata)
   - `memory_vectors` (sqlite-vec, for semantic search)
   - `memory_fts` (FTS5 BM25, for keyword search)

**Check it saved** — two ways to verify:

**Quick check via `/recall`** (file-grep synthesizer; searches CLAUDE.md / README / docs / code):

```
/recall refresh token
```

`/recall` does not query the memory MCP directly — it surfaces what's already in your project's knowledge files. Useful for cross-referencing, but it won't show vector-ranked hits.

**Full search via the `memory_search` MCP tool** (semantic + keyword hybrid against `memory.db`):

Ask Claude to call it directly: *"search my memories for 'refresh token'"*. Expected output:

```
Memory Search: "refresh token"
================================
score=0.94  importance=8  conf=0.90
[context] The refresh token endpoint accepts expired access tokens as proof
of identity — this is intentional. docs/auth-flow.md. Don't add a validation
check that rejects expired tokens here.
Tags: auth, refresh-token, intentional-design
Saved: 2026-04-28 14:33:01
```

The score is the hybrid rank: 70% vector similarity + 30% BM25, then
multiplied by confidence. A high-confidence learning ranks above a tentative
one with the same text.

---

## Day 1 — Manual save via the MCP tool directly

You can also save memories outside of `/learn` — directly from the Python
REPL, for testing or automation:

```python
# From memory-mcp/ with venv active
from db import MemoryDB

db = MemoryDB("/tmp/walkthrough-demo.db")

id_a = db.save(
    content="Payment webhook handler retries 3 times on network timeout, exponential backoff",
    category="context",
    project="my-web-app",
    tags=["payments", "webhooks", "retry"],
    importance=8,
    confidence=0.95,
)
print(f"Saved: {id_a[:8]}...")
# Saved: 3f8a91b2...
```

---

## Day 2 (later session) — `/recall` brings it back

New session. Claude's context window is fresh. You're about to work on
the payment retry logic.

```
/recall payment retry
```

```
Memory Search: "payment retry"
================================
score=0.91  importance=8  conf=0.95
[context] Payment webhook handler retries 3 times on network timeout,
exponential backoff.
Tags: payments, webhooks, retry
Saved: 2026-04-27 09:12:44

score=0.78  importance=6  conf=0.80
[context] Retry utility in src/utils/retry.py — use this instead of
rolling per-service retry logic.
Tags: retry, patterns, utils
Saved: 2026-04-15 16:45:02
```

Two results. The top one is your specific payment webhook note. The second
is a general retry pattern captured earlier. Both surfaced from a
four-word query. The vector search found "payment retry" semantically;
the BM25 pass found keyword overlap. The hybrid score is the union, ranked.

**Without this:** you re-read the webhook handler to rediscover the retry
count, check whether there's a shared utility, and hope you remember the
backoff strategy.

**With this:** `score=0.91` tells you the top result is a strong match.
One line of context, ready to act on.

---

## Realistic REPL output — hybrid search

```python
from db import MemoryDB
from hybrid_search import hybrid_search

db = MemoryDB("/tmp/walkthrough-demo.db")
results = hybrid_search(db, "webhook retry timeout", None, project="my-web-app")

for r in results[:3]:
    print(f"  score={r['score']:.3f}  conf={r['confidence']}  content={r['content'][:60]}...")
```

```
  score=0.847  conf=0.95  content=Payment webhook handler retries 3 times on network ti...
  score=0.612  conf=0.80  content=Retry utility in src/utils/retry.py — use this instea...
  score=0.441  conf=0.30  content=Celery task timeout is 30s by default, configurable v...
```

The third result has `conf=0.30` — it was saved as tentative. Despite
having some keyword overlap, its confidence multiplier pulls it below the
others. The system weights certainty, not just relevance.

---

## What memory is NOT for

**1. Secrets or credentials.** The database is local SQLite, not encrypted
at rest. Never save API keys, passwords, or tokens via `memory_save`. Use
your OS keychain or a secrets manager.

**2. Ephemeral state.** "The build is currently broken" is a fact that's
wrong in 20 minutes. Don't save it — it will surface as stale context in
future sessions and mislead Claude. Memory is for durable patterns, not
current status.

**3. Verbatim conversation logs.** Memory entries are structural metadata:
decisions, patterns, corrections, learnings. Saving full message bodies
bloats the database, degrades search precision, and defeats the purpose —
the value is distilled knowledge, not transcript replay.

---

## Cross-link

Why does memory live in the toolkit but the database live in `~/.claude/`?
The boundary is intentional and documented in [docs/ADR-MEMORY-BOUNDARY.md](../docs/ADR-MEMORY-BOUNDARY.md).
Short answer: the toolkit ships the code; your knowledge stays with you,
not in the repo.
