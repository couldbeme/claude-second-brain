# OSS Adoption Checklist

A 2-minute fit-check before you commit time to setup.

---

## Seven questions

Answer yes or no. One-liners explain why each one matters.

**1. Do you use Claude Code daily (or near-daily)?**
The toolkit is a Claude Code layer. Without Claude Code as the host, nothing works.

**2. Do you repeat multi-step workflows across sessions?**
Repeated workflows are the raw material for slash commands. No repetition = no compounding.

**3. Do you want Claude to remember things between sessions?**
The memory system gives Claude persistent knowledge of your project. Without cross-session need, memory setup cost isn't worth it.

**4. Do you care about consistent code quality gates (tests, lint, build)?**
`/verify` and `/commit-push-pr` enforce these before any commit leaves your machine. If you have no quality bar to protect, these commands add friction with no payoff.

**5. Do you want prompt engineering to compound over time?**
`/metaprompt` turns fuzzy asks into structured, reusable prompts. The compounding only happens if you save and reuse outputs. If you prefer ad-hoc, skip this one.

**6. Are you working solo or on a small team (2–8 people)?**
The toolkit is calibrated for individual and small-team use. Large org rollout has operational considerations covered in [TOOLKIT.md](../TOOLKIT.md).

**7. Are you comfortable with open-source tooling (SQLite, Python, local LLM server)?**
The memory system runs locally: SQLite database, Python MCP server, optional LM Studio for semantic search. No SaaS dependency. If you need managed infra, this stack is wrong.

---

## Decision rule

- **3+ yes** → Start with `/guide tour`. The core commands (orient, build, ship) will give you value without memory setup.
- **5+ yes** → You'll get strong returns. Set up memory ([SETUP-MEMORY.md](../SETUP-MEMORY.md)) after your first session — don't skip it.
- **7/7 yes** → This toolkit was built for your workflow. Read [TOOLKIT.md](../TOOLKIT.md) for the full picture.

---

## You might not be a fit if

- You don't control your Claude Code environment (IT-managed, restricted extensions).
- Your project has strict data residency requirements — the memory database is local, but embedding calls go to a local LM Studio instance, not the cloud. Verify this is acceptable before setup.
- You're evaluating AI tooling for a large org procurement decision. This is an OSS practitioner toolkit, not an enterprise product with SLAs.

---

## Start here

[QUICK-START.md](../QUICK-START.md) — install takes 30 seconds, first command tour takes 5 minutes.
