# /resolve-pr — Hands-On Walkthrough

## What it does

`/resolve-pr` fetches review comments from an open pull request, addresses
each one in code, and drafts a polite reply per comment explaining the fix.
It's the difference between spending 40 minutes context-switching through
reviewer feedback and spending 5 minutes confirming Claude's work.

The command doesn't merge, doesn't auto-approve, and doesn't push without
your confirmation. It handles the mechanical part — reading the comments,
mapping them to code, making targeted fixes — while you retain final
judgment on every change.

---

## Setup — fictional PR

We'll use a fictional PR to make the mechanics concrete. The PR adds a
`/api/users/search` endpoint.

**The diff (fictional):**

```python
# src/api/users.py  (fictional)

@router.get("/users/search")
def search_users(term: str, db: Session = Depends(get_db)):
    query = f"SELECT * FROM users WHERE name LIKE '%{term}%'"  # line 47
    results = db.execute(query)
    return results.fetchall()
```

**Three review comments (fictional):**

> **Reviewer (line 47):** SQL injection — never interpolate user input into
> a query string. Use parameterized queries.

> **Reviewer (line 47):** This returns all columns including password_hash.
> Select only the fields the client actually needs.

> **Reviewer (function signature):** No pagination — if the table has 100k
> users a search for "a" returns everything. Add `limit` and `offset`.

These are the three comments `/resolve-pr` will work through.

---

## Run `/resolve-pr`

```
/resolve-pr https://github.com/<your-org>/<your-repo>/pull/42
```

Claude fetches the review comments from the GitHub API, reads the
diff context, and produces a structured fix plan:

```
Fetched 3 review comments on PR #42
Analyzing: src/api/users.py

Fix plan:
  [1] SQL injection (line 47) — CRITICAL
      Parameterize query using SQLAlchemy text() with bound params.

  [2] Column exposure (line 47) — HIGH
      Select id, name, email only. Exclude password_hash and internal fields.

  [3] Missing pagination (function signature) — MEDIUM
      Add limit: int = 50, offset: int = 0 params. Cap limit at 200 server-side.

Proceed with all 3 fixes? [yes/no/pick]
```

You confirm. Claude applies the fixes:

**The fixed code (fictional):**

```python
# src/api/users.py — after /resolve-pr  (fictional)

from sqlalchemy import text

@router.get("/users/search")
def search_users(
    term: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if limit > 200:
        limit = 200
    query = text(
        "SELECT id, name, email FROM users "
        "WHERE name LIKE :pattern LIMIT :limit OFFSET :offset"
    )
    results = db.execute(query, {"pattern": f"%{term}%", "limit": limit, "offset": offset})
    return results.fetchall()
```

**The draft replies (fictional):**

> **Reply to comment 1 (SQL injection):**
> Fixed — switched to a parameterized query via SQLAlchemy `text()` with
> bound parameters. The `term` value is now passed as `:pattern` and never
> interpolated into the query string.

> **Reply to comment 2 (column exposure):**
> Fixed — changed `SELECT *` to `SELECT id, name, email`. `password_hash`
> and other internal fields are no longer returned.

> **Reply to comment 3 (pagination):**
> Fixed — added `limit` (default 50, max 200) and `offset` parameters.
> The server-side cap prevents unbounded queries even if the client sends
> `limit=999`.

---

## What `/resolve-pr` does NOT do

- **Won't merge.** It fixes code and drafts replies. Merging is your decision after review.
- **Won't auto-approve.** Review approval requires a human judgment call on whether the fixes are correct. Make that call yourself.
- **Won't push without asking.** After fixes are applied, Claude asks whether to commit and push. Default is to show you the diff first.
- **Won't handle all comment types.** Design feedback, questions, and "please rewrite the whole approach" comments are surfaced to you as unresolved — Claude won't guess at architectural intent.

---

## When to use it

- PR has 3+ discrete, actionable code comments (not design debates).
- Comments map to specific lines — not "this whole file needs restructuring."
- You want to respond to reviewers the same day, not let the PR stagnate.
- Reviewer feedback is blocking a merge and you need to clear it fast.

## When NOT to use it

- The PR has unresolved design disagreements that aren't settled yet. Closing
  code comments before the design question is answered wastes both parties' time.
- You don't understand what the reviewer is asking. Resolve that ambiguity
  in comments before running the command — Claude will interpret, not clarify.
- The PR touches security-critical code and you want to review every line
  personally. Use `/resolve-pr` for the mechanical fixes, then do a
  `/audit security` pass before pushing anything.
