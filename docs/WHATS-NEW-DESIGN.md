# `/whats-new` — Design

> **Status.** v0.1, 2026-05-06. Companion to `/self-audit` (`memory-mcp/self_audit.py`). Resolves the `[unverified]` evidence string `"feature unverified — refresh catalog via /whats-new"` emitted by `/self-audit`.

## Goal

Surface new Claude Code platform features (hooks, skills, slash commands, MCP, settings.json schema, model defaults, CLI flags) since the last local check, deterministically and offline-tolerant. Closes the catalog-refresh loop for `/self-audit`.

**Non-goals.** Not a release-notes archive. Not a rollback tool. Not LLM-mediated — every parse step is regex / structural.

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│ /whats-new (CLI / slash command)                               │
│   ↓                                                            │
│ memory-mcp/whats_new_check.py                                 │
│   ├─ load_state()       ← whats_new_state.json (ETag, seen)   │
│   ├─ fetch_releases()   ← api.github.com/.../releases          │
│   ├─ diff(state, fetched)                                      │
│   ├─ categorize(release.body) — regex-match bullets to buckets │
│   ├─ format_report(--text|--markdown|--json)                  │
│   └─ save_state()       → whats_new_state.json                │
└───────────────────────────────────────────────────────────────┘
```

Stdlib-only. Same zero-deps stance as `self_audit.py`. No `requests`, no `httpx`. `urllib.request` + `json` + `re`.

## Source

- **URL:** `https://api.github.com/repos/anthropics/claude-code/releases?per_page=20`
- **User-Agent (required):** `claude-second-brain-whats-new/0.1`
- **Conditional GET:** `If-None-Match: <last_etag>` → 304 short-circuit.
- **Negative-result fallback:** if the GitHub API ever returns 5xx or the user passes `--no-network`, replay the last cached diff and exit 0 with `[OFFLINE]` marker. Detail in [§ Failure modes](#failure-modes).

Full source verification at `~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/launch_archive/whats-new-recon-2026-05-06.md`.

## State file

**Path:** `~/.claude/projects/-Users-macbook-Dev/memory/whats_new_state.json`

**Schema:**

```json
{
  "schema_version": 1,
  "last_checked_at": "2026-05-06T14:30:00Z",
  "last_checked_version": "v2.1.131",
  "last_etag": "W/\"5157861e1a1b7a65a9...\"",
  "seen_releases": [
    {"tag": "v2.1.131", "published_at": "2026-05-05T17:42:11Z"},
    {"tag": "v2.1.130", "published_at": "2026-05-04T11:20:00Z"}
  ]
}
```

**Bounds:** `seen_releases` rotates FIFO at 200 entries (~2 years at current cadence). `schema_version` enables forward-compatible migrations.

**Atomic write:** `tempfile.NamedTemporaryFile(dir=...)` + `os.replace()` — never partial writes that corrupt state.

## Categorization

Release bodies are markdown bullets. Categorization runs a regex match on each bullet to assign a bucket. Bucket map (open-set; "misc" catches unmatched):

| Bucket | Trigger keywords (case-insensitive) |
|---|---|
| Hooks | `hook`, `PreCompact`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SessionStart` |
| Skills | `skill`, `SKILL.md` |
| MCP | `mcp`, `MCP server`, `tool` (in MCP context) |
| Slash Commands | `slash command`, `/[a-z-]+ command`, `command:` |
| Settings | `settings.json`, `setting:`, `config flag` |
| Model | `model:`, `opus`, `sonnet`, `haiku`, `claude-` + version |
| CLI | `--[a-z-]+` flag, `claude --`, CLI argument |
| Misc | unmatched bullets — never dropped |

**Rationale.** The `/self-audit` rule categories (CMD, AGENT, SKILL, TMPL, SESSION) drive what changes matter. Bucketed output makes the next-`/self-audit`-pass mapping obvious.

## CLI surface

```
whats_new_check.py [--format text|markdown|json]
                   [--since <tag>]
                   [--no-network]
                   [--state-file <path>]
                   [--quiet]
```

| Flag | Behavior |
|---|---|
| `--format text` (default) | Human terminal output, ANSI-light, grouped by bucket |
| `--format markdown` | Pasteable into a doc; group headings as `##`, bullets verbatim |
| `--format json` | Structured: `{ "new_releases": [...], "buckets": {...}, "skipped": [...] }` |
| `--since v2.1.100` | Ignore `seen_releases`, list everything after this tag |
| `--no-network` | Replay last cached diff, mark `[OFFLINE]` |
| `--state-file <path>` | Override default state-file path (testing) |
| `--quiet` | Suppress informational lines; emit only the diff |

**Exit codes:** `0` always on success or no-new-releases. `1` only on hard errors (malformed state file, JSON decode failure on `body`). Network failures → `0` with `[OFFLINE]` marker (graceful degradation, not a CI gate).

## Diff algorithm

Set difference on `tag_name`. Order preserved by `published_at` descending. Pseudocode:

```python
def diff(state, fetched):
    seen = {r["tag"] for r in state["seen_releases"]}
    new = [r for r in fetched if r["tag_name"] not in seen]
    new.sort(key=lambda r: r["published_at"], reverse=True)
    return new
```

Deterministic. Same state + same fetch payload = same output.

## Failure modes

| Condition | Behavior | Exit code |
|---|---|---|
| Network timeout (10s) | `[OFFLINE] timeout — replaying cached diff`, output last known state | 0 |
| HTTP 403 (rate limit) | `[RATE-LIMIT] reset at <X-RateLimit-Reset>`, no fetch attempted | 0 |
| HTTP 304 (not modified) | `no new releases since <last_checked_version>` | 0 |
| HTTP 5xx | `[UPSTREAM-ERROR] GitHub returned <status>; replaying cached diff` | 0 |
| Malformed response JSON | `[ERROR] could not parse GitHub response` to stderr | 1 |
| State file missing | First run; treat as `seen_releases: []`, fetch + cache normally | 0 |
| State file malformed JSON | `[ERROR] state file corrupt at <path>; aborting` to stderr; do NOT overwrite | 1 |
| `--no-network` set | Skip fetch; output `[OFFLINE] cached state from <last_checked_at>` | 0 |

**Key invariant.** Never overwrite a malformed state file — corrupt state should fail loud, not silently reset.

## Test surface

`memory-mcp/tests/test_whats_new.py`. Mirror `test_self_audit.py` patterns:

- **Fixtures:** `tmp_state_file`, `mock_urlopen` (monkeypatch `urllib.request.urlopen`)
- **State-file tests:** load missing → empty default; load malformed → raise; save atomic; FIFO rotation at 200
- **Fetch tests:** 200 OK, 304 not-modified, 403 rate-limit, 5xx server-error, network timeout
- **Diff tests:** all-new, all-seen, partial overlap, empty fetch
- **Categorize tests:** each bucket's regex; misc fallback; multi-bucket bullet (assigned to first match)
- **Format tests:** text / markdown / json shapes; `--since` override; `--no-network` reads cache
- **Integration:** end-to-end with mocked HTTP — verify exit codes, stdout, state-file updates

**Target:** ≥ 30 tests. Match `test_self_audit.py`'s deterministic style — no real HTTP, ever.

## Integration with `/self-audit`

After `/whats-new` runs, the user can re-run `/self-audit`:
- Catalog entries with `status: unverified` should be reviewed against new buckets.
- The `evidence` string `"feature unverified — refresh catalog via /whats-new"` becomes actionable: the user has the diff, can verify, and can manually flip the catalog entry to `status: verified`.

**Phase 6C stretch goal (not in v0.1).** Auto-update `self_audit_catalog.json` from `/whats-new` output — would close the loop fully but requires LLM-assisted bullet-to-rule mapping. Defer.

## Skill artifact

`skills/whats-new/SKILL.md` — frontmatter + body mirroring `skills/self-audit/SKILL.md`:

- `description:` one-liner that names the source (GitHub releases) so users know to expect a network call.
- `argument-hint:` `Optional flags (e.g., "--since v2.1.100", "--format markdown", "--no-network")`
- Body: what it checks, run examples, exit codes, failure modes, when-to-use / when-NOT-to-use.

## Symlink + slash command

```bash
ln -sf ~/Dev/claude-second-brain/skills/whats-new ~/.claude/skills/whats-new
```

Slash command at `commands/whats-new.md` mirrors `commands/audit.md` — thin shim that delegates to the skill (Claude Code surfaces the skill body via the `whats-new` command).

## Open decisions

| # | Question | Recommendation |
|---|---|---|
| 1 | `seen_releases` cap | 200 entries, FIFO rotation |
| 2 | First-run behavior | Don't dump 200 historical releases; mark `last_checked_version` to current latest, emit "first run — establishing baseline" |
| 3 | `--no-network` and missing state | Emit `[ERROR] no cached state and --no-network specified`, exit 1 |
| 4 | Auto-update catalog | Defer to Phase 6C |
| 5 | Optional `SessionStart` hook to auto-fire | Defer to Phase 6C; user can run `/whats-new` manually for v0.1 |

## Implementation checkpoints

1. `whats_new_check.py` skeleton — argparse, no-op handlers (~30 LOC). Verify CLI parses.
2. State-file load/save with atomic write + FIFO rotation. ~8 tests.
3. Fetch with conditional GET, all 5 HTTP cases. ~8 tests.
4. Diff + categorize. ~10 tests.
5. Format output (3 modes). ~6 tests.
6. End-to-end main(). ~3 integration tests.
7. SKILL.md + commands/whats-new.md.
8. Symlink + smoke test against live API.

**Estimated total LOC:** ~280 module + ~350 test = ~630.
