# Source-registry schema (`sources/<scout>.yaml`)

Every autonomous scout owns one registry file declaring **what it reads, how it
reads it, how fresh it must be, and which actions are gated**. The registry is the
contract between a scout's mandate and the honest-autonomy line: *gathering is free;
acting in the world is gated.*

> **X is the primary signal source** (operator directive, 2026-06-01). The default
> access tier is **free web recon** (`access: web_search`) — $0, ToS-respecting
> (search over indexed X content, not scraping-against-terms). An operator-provided
> `X_BEARER_TOKEN` unlocks the paid `x_recent_search` tier with **no schema change** —
> the registry already declares it; it just goes `enabled: false → true`.

## Top-level fields

```yaml
scout: <kebab-name>            # matches the filename: trend-scout.yaml -> trend-scout
mandate: <one line>            # what this scout is FOR
schedule:                      # native autonomy host (/schedule cron OR Workflow)
  cron: "0 13 * * *"           # when it runs unattended (UTC)
  host: schedule               # schedule | workflow | loop — all native Claude Code
budget:
  run_ceiling_usd: 0.00        # hard cap per run; 0.00 = free-web-only, never spend
  cost_ledger: true            # maintain a running $ ledger, stop before crossing cap
sinks:                         # where findings land (DB canonical + Obsidian mirror)
  belief_db: true              # canonical store — dedup/contradiction/confidence free
  obsidian_vault: "${OBSIDIAN_VAULT:-./intel-vault}"   # human-facing mirror (config)
sources:                       # the list below
  - ...
```

## A `sources[]` entry

```yaml
- id: <unique-within-scout>
  type: x | rss | api | mcp_connector | web        # the SHAPE of the source
  access: web_search | x_recent_search | rss | http_api | mcp   # HOW we read it
  enabled: true | false                            # paid tiers ship disabled
  # --- the query surface (type-specific) ---
  query: "agent memory drift OR forgets instructions"   # x / web search terms
  handles: ["@user1", "@vc2"]                       # x: specific accounts to watch
  list_id: "..."                                    # x: a curated X list id
  url: "https://news.ycombinator.com/rss"           # rss / api endpoint
  lookback: 7d                                      # recency window
  # --- freshness + governance ---
  freshness:
    poll_every: 24h                                 # how often the scout re-reads
    stale_after: 72h                                # findings older than this = flagged stale
  credential_env: X_BEARER_TOKEN                    # env var name IF a key is needed; never a literal
  gated_actions: [post, reply, follow, dm, like]    # actions that MUST pass the commitment-gate
  cost_per_call_usd: 0.005                           # estimate for the ledger (0 for web)
  provenance_required: true                         # every finding cites a real URL or is INFERRED
```

## Access tiers for X (the directive, made concrete)

| tier | `access` | cost | what it returns | needs |
|---|---|---|---|---|
| **Free web** (default) | `web_search` | $0 | X posts/threads that are web-indexed, via WebSearch/WebFetch over `site:x.com` + nitter mirrors + quote-tweets surfaced in search | nothing |
| **Paid recent-search** | `x_recent_search` | ~$0.005/read | structured 7-day `GET /2/tweets/search/recent` + engagement metrics | operator-provided `X_BEARER_TOKEN` (env, local-only) |

Both reuse `/x-launch-recon`'s discipline verbatim: secrets from env only, cost ledger,
free-web-first, **degrade gracefully** (if the paid tier is unavailable, fall back to
web and SAY SO — never silently skip), and never fabricate engagement numbers.

## The honesty line, encoded

- **Reads are free and ungated.** A scout may gather autonomously from any `enabled`
  source with no human in the loop.
- **`gated_actions` pass the commitment-gate.** Any outward/spend/account action
  (post, reply, follow, dm, like, account-creation, paid-call-over-ceiling) is routed
  through `memory-mcp/commitment_gate_hook.py` + explicit operator authorization.
  *The scout never covertly self-registers, solves CAPTCHAs, or spends past the ceiling.*
- **`credential_env` names an env var, never holds a value.** No key, prefix, or
  token ever lands in a tracked file (CLAUDE.md rule 13). Operator secrets live local.
- **`provenance_required: true`** means every stored finding carries a real source URL
  or is explicitly tagged INFERRED. No invented evidence (x-launch-recon hard rule 4).

## Validation

A registry is valid when: filename stem == `scout`; every paid-tier source
(`cost_per_call_usd > 0`) declares a `credential_env` AND ships `enabled: false` until
the key is present; every source sets `freshness`; `budget.run_ceiling_usd` is present.
See `sources/trend-scout.yaml` for the worked X-first example.
