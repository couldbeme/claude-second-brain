# Continuity Research: Cross-Session Memory Patterns Survey

**Audit:** 2026-04-29
**Scope:** Adopt / Adapt / Reject decisions for the Continuity preservation system

---

## 1. Summary

Cross-session continuity in LLM agent systems falls into three dominant patterns: append-only event logs with replay (Anthropic Managed Agents, claude-flow), hook-triggered compression into semantic summaries (claude-mem), and explicit memory-block stores with vector retrieval (Letta, mem0). Consensus is forming around separating ephemeral context from durable storage, and around hybrid compaction strategies that preserve voice and decision rationale better than raw summarization. The genuine gap across all surveyed systems is preservation of *decision rationale and voice tone* — systems reliably persist facts but consistently lose the "why" behind choices and the stylistic register of prior exchanges.

---

## 2. Per-System Snapshots

### 2.1 Letta Multi-Session Memory

Letta agents use a three-tier architecture: core memory blocks (always in-context, RAM analogue), archival memory (vector store, disk analogue), and recall memory (full conversation log with date and text search). Each memory block carries a `block_id`, label, character limit, and string value; these are persisted in a database and recompiled into context on every call. Shared blocks can be attached to multiple agents simultaneously, enabling cross-agent state without message passing. Failure mode: if the DB is unavailable at session start, no context is injected and the agent begins blank with no error surfaced to the user.

- Adopt the labeled-block model for structured persistence (block_id, label, limit)
- Adapt the archival recall — their vector search is agent-scoped; we need project-scoped
- The three-tier RAM/disk/log metaphor maps cleanly to our working-memory/checkpoint/full-log layers

Sources: [Letta Memory Blocks blog](https://www.letta.com/blog/memory-blocks), [Letta memory management docs](https://docs.letta.com/advanced/memory-management/)

---

### 2.2 mem0 User-Context Module

mem0's `add()` pipeline extracts facts from raw messages, runs vector similarity against existing memories, then executes ADD/UPDATE/DELETE/NOOP operations. Cross-session retrieval combines a conversation summary (semantic aggregate of full history) with a sliding window of m=10 recent messages, fetching the top s=10 semantically similar stored memories at query time. Metadata per entry: entity type, embedding vector, creation timestamp (graph variant); base variant stores natural language strings with timestamps. Distributed failure mode: when multiple instances serve one user, a write by one instance may not propagate before another instance handles the next request, causing the agent to act on stale memory.

- The ADD/UPDATE/DELETE/NOOP lifecycle is directly adoptable for our contradiction resolution
- Their dual-source retrieval (summary + sliding window) is more robust than pure vector search
- Reject their cloud-required graph variant for local-only deployments

Sources: [mem0 paper arXiv:2504.19413](https://arxiv.org/html/2504.19413v1), [mem0 memory types docs](https://docs.mem0.ai/core-concepts/memory-types), [mem0 AI memory layer guide](https://mem0.ai/blog/ai-memory-layer-guide)

---

### 2.3 claude-mem Auto-Capture (Alex Newman / thedotmack)

Five lifecycle hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd) capture raw tool I/O without manual intervention. The Stop hook runs a two-stage AI compression: raw observations → semantic summaries capturing key decisions and outcomes. SessionStart queries SQLite + ChromaDB by project directory and injects matching summaries into the system prompt before the first user message. Known failure modes from GitHub issues: (a) Stop hook returns "next steps" text that Claude interprets as new work directives, creating an infinite session loop (issue #987); (b) SessionStart hook stderr usage shows as 'error' in Claude Code UI (issue #1181); (c) Stop hook output can trigger JSON validation failures (issue #1290).

- The PostToolUse capture pattern is directly adoptable — it's the most comprehensive raw signal
- The infinite-loop failure is a critical risk for our Stop hook: summary output must not contain imperative language
- The two-stage compression model (raw → semantic) aligns with our approach; their compression prompt leaks are the gap

Sources: [claude-mem GitHub](https://github.com/thedotmack/claude-mem), [Stop hook loop issue #987](https://github.com/thedotmack/claude-mem/issues/987), [SessionStart error issue #1181](https://github.com/thedotmack/claude-mem/issues/1181), [paperclipped.de write-up](https://www.paperclipped.de/en/blog/claude-mem-persistent-memory-ai-coding-agents/)

---

### 2.4 Generative Agents Memory Stream (Park et al., arXiv:2304.03442)

Each memory entry stores: textual observation, creation timestamp, last-access timestamp, and an importance score (1–10, LLM-rated). Retrieval score = weighted sum of normalized recency (exponential decay on last-access time) + importance + cosine similarity to query embedding. Reflection triggers when the cumulative importance of recent memories exceeds a threshold; the 100 most recent memories are synthesized into higher-level insights stored as new memory objects. This is a within-simulation architecture — it does not address explicit session-boundary handling or disk persistence; continuity is a property of the running simulation, not of save/restore.

- The recency + importance + cosine scoring formula is directly adoptable for our retrieval ranking
- Reflection-on-threshold is adaptable: trigger checkpoint summarization when session importance accumulates past a configurable value
- Reject as a session-bridging mechanism — it assumes continuous runtime, not cold-start recovery

Sources: [arXiv:2304.03442](https://arxiv.org/abs/2304.03442), [Portkey summary](https://portkey.ai/blog/generative-agents-interactive-simulacra-of-human-behavior-summary/), [gonzo substack analysis](https://gonzoml.substack.com/p/generative-agents-interactive-simulacra)

---

### 2.5 claude-flow Swarm Session-Bridging

claude-flow v2/v3 uses a daemon process with memory-coordinator and swarm-memory-manager components for distributed state. Cross-agent state is passed through a shared memory layer; the v3 always-on daemon refreshes state every 5 seconds and persists to disk with claimed 65% compression efficiency and 27.3 MB active memory ceiling. Session resume is described as "auto-restore." The architecture documentation does not specify what data survives a daemon crash vs. a clean shutdown, nor does it specify the storage format beyond "persistent memory storage." Public documentation is sparse; the v3 is described as a complete rebuild (January 2026) with limited production track record.

- The memory-coordinator pattern for multi-agent state is worth monitoring; insufficient documentation to adopt now
- 65% compression claim has no cited methodology — treat as unverified
- Reject for adoption until documented failure recovery is published

Sources: [claude-flow wiki](https://github.com/ruvnet/claude-flow/wiki/Agent-System-Overview), [v2 release issue #113](https://github.com/ruvnet/claude-flow/issues/113)

---

### 2.6 Anthropic Managed Agents Memory

The managed agents architecture decouples the harness (stateless, replaceable) from a durable session log. The harness writes events via `emitEvent(id, event)`; on crash, a new harness instance calls `getSession(id)` and replays from the last recorded event. The memory tool (type: `memory_20250818`) operates client-side: Claude makes tool calls to view/create/str_replace/insert/delete files in a `/memories` directory that the caller implements. Every memory write creates an immutable version with a `memver_` prefix; rollback is a read-then-rewrite of any prior version. A `redact` endpoint scrubs content from historical versions while preserving audit metadata. The default system prompt injected when memory is enabled instructs Claude to "ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE." Failure mode: if the client-side storage is unavailable, the memory tool calls fail silently (return errors) but the session continues without memory context; no fallback or warning in system prompt.

- The immutable versioned writes with `memver_` prefix is directly adoptable for our audit trail
- The event-log replay pattern for crash recovery is directly adoptable
- The client-side storage model matches our local-only constraint — this is our closest architectural peer

Sources: [Anthropic memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool), [Anthropic managed agents engineering post](https://www.anthropic.com/engineering/managed-agents)

---

### 2.7 OpenAI Workspace Agents Persistent Workspace

Workspace Agents (launched April 2026, research preview) are powered by Codex cloud sessions. Persistence is folder-based: the agent writes notes, drafts, and outputs to a persistent folder between sessions. Codex can "schedule future work and wake up on its own" across days or weeks. Memory is cloud-stored under OpenAI's infrastructure; there is no documented local-only or export option. What persists: files written to the workspace folder, agent-level behavioral preferences. What does not persist: full conversation transcript (only summarized context is carried forward). Failure mode: workspace folder contents survive session interruption, but if a Codex cloud session is interrupted mid-write, partial file state may be inconsistent; no documented atomic write guarantee.

- The "initializer session bootstraps memory structure before work begins" pattern (Anthropic's paired docs) is more actionable than OpenAI's vague "persistent folder"
- Cloud-only posture is incompatible with our local-first constraint — reject for adoption
- The scheduler/wake-up pattern is interesting for scheduled checkpoint generation but requires cloud infrastructure we don't have

Sources: [OpenAI workspace agents announcement](https://openai.com/index/introducing-workspace-agents-in-chatgpt/), [VentureBeat write-up](https://venturebeat.com/orchestration/openai-unveils-workspace-agents-a-successor-to-custom-gpts-for-enterprises-that-can-plug-directly-into-slack-salesforce-and-more)

---

### Compaction Research Summary

JetBrains Research (Dec 2025, SWE-bench Verified): observation masking outperforms LLM summarization in reliability and cost, cutting expenses by ~52% vs. baseline; LLM summarization caused agents to run 15% longer because summaries smoothed over stop signals. The hybrid model (masking first, summarization only when severely unwieldy) adds another 7–11% cost reduction. mem0's production data: 91% lower p95 latency and >90% token cost reduction vs. naive RAG with full history. Critical industry finding: ~65% of enterprise AI failures in 2025 were attributed to context drift or memory loss during multi-step reasoning.

Sources: [JetBrains Research post](https://blog.jetbrains.com/research/2025/12/efficient-context-management/), [mem0 paper arXiv:2504.19413](https://arxiv.org/html/2504.19413v1), [Zylos AI compaction research](https://zylos.ai/research/2026-02-28-ai-agent-context-compression-strategies)

---

## 3. Comparison Table

| System | Preserves Voice | Preserves Decision Rationale | Local-Only | Hooks or Loop | Primary Failure Mode |
|---|---|---|---|---|---|
| Letta | No | Partial (archival recall) | Yes (OSS) | Loop (API call) | DB unavailable → blank context |
| mem0 | No | No | No (cloud default) | Loop (add/search) | Stale memory in distributed writes |
| claude-mem | Partial (summaries) | Partial (key decisions) | Yes | Hooks (Stop/SessionStart) | Stop hook infinite loop on imperative summary text |
| Generative Agents | No | No | Simulation-only | Loop (reflection threshold) | No cold-start recovery; continuous runtime assumed |
| claude-flow | Unknown | Unknown | Yes (daemon) | Daemon + hooks | Crash recovery undocumented |
| Anthropic Managed Agents | No | Partial (event log) | Client-side | Loop (tool calls) | Client storage fail → silent context loss |
| OpenAI Workspace Agents | No | No | No (cloud-only) | Loop (folder writes) | Mid-write interruption → inconsistent file state |

---

## 4. Adopt / Adapt / Reject

### Adopt Directly

- **Immutable versioned writes (Anthropic `memver_` pattern).** Every memory write generates a timestamped version; rollback is read-then-rewrite of any prior version. Audit trail is preserved even after content is redacted. This fits our local-first filesystem without modification.
- **Event-log replay for crash recovery (Anthropic Managed Agents).** Harness is stateless; all state lives in a durable session log. On crash, new harness replays from last recorded event. Directly maps to our checkpoint.md pattern.
- **Recency + importance + cosine retrieval scoring (Park et al.).** Normalized weighted sum of exponential-decay recency, LLM-rated importance (1–10), and embedding cosine similarity. Gives older but high-importance memories priority over recent but trivial ones.
- **PostToolUse capture for raw signal (claude-mem).** Every tool call input+output is recorded; this is the most granular signal available and enables any downstream compression strategy.

### Adapt with Modification

- **Two-stage compression (claude-mem Stop hook → semantic summary).** The pattern is sound but the Stop hook failure mode is critical: summary output must be declarative-only (past tense, no imperatives, no "next steps" phrasing) to prevent the infinite-loop failure documented in claude-mem issue #987. Our implementation should emit summaries to a file rather than returning them as hook output to Claude's context.
- **ADD/UPDATE/DELETE/NOOP memory lifecycle (mem0).** The contradiction-resolution lifecycle is correct but their implementation requires a cloud inference call per `add()`. Adapt by running the deduplication/merge step locally against the markdown memory store using embedding similarity, triggered on SessionEnd rather than on every message.
- **Observation masking before summarization (JetBrains Research).** Apply masking (replace tool outputs with placeholders) as the first-pass compaction; trigger LLM summarization only when context exceeds a token threshold. Do not use summarization as the default path — it smooths over stop signals and costs more.

### Reject

- **Generative Agents reflection mechanism for session bridging.** Designed for continuous simulation runtime; has no cold-start recovery model.
- **OpenAI Workspace Agents folder model.** Cloud-only, no export or local-first option, no documented atomic write guarantee, privacy posture incompatible with local-first requirement.
- **claude-flow swarm memory.** Insufficient public documentation on failure recovery, unverified compression claims, v3 is a January 2026 rebuild with no production track record. Revisit in 6 months.

---

## 5. Open Questions for the Architect

1. **Voice and tone preservation.** No surveyed system captures voice register or communication style across sessions. Should our checkpoint store a voice profile (tone words, formality score, example phrasings) as a separate memory block, distinct from factual context? If yes, what triggers its update?

2. **Stop hook output safety contract.** The claude-mem infinite-loop failure shows that any Stop hook returning text to Claude's context risks being interpreted as work directives. Should our Stop hook write to disk only and return an empty response to Claude, or is there a safe format for injecting declarative-only content?

3. **Importance scoring authority.** Park et al. use LLM self-rating (1–10) for importance. Mem0 uses extraction heuristics. Our system currently uses human-assigned importance. Should importance be LLM-assigned at write time, human-assigned, or a hybrid where human assignment overrides LLM defaults? How does importance decay over sessions?

4. **Contradiction handling at session start.** When SessionStart injects prior memory and the current session produces facts that contradict stored memory, no surveyed system has a documented real-time resolution protocol. Should our system surface contradictions inline, defer resolution to SessionEnd, or run a background reconciler?

5. **Compaction boundary preservation.** JetBrains Research found LLM summarization smooths over stop signals; Anthropic's docs recommend pairing memory with compaction to preserve critical information. What constitutes "critical" for our system — is it a content classification problem (decisions, voice, in-flight tasks) or a structural one (anything written to memory by the agent is critical by definition)?

---

## 6. Sources

1. [Letta Memory Blocks blog](https://www.letta.com/blog/memory-blocks)
2. [Letta advanced memory management docs](https://docs.letta.com/advanced/memory-management/)
3. [mem0 paper — arXiv:2504.19413](https://arxiv.org/html/2504.19413v1)
4. [mem0 memory types docs](https://docs.mem0.ai/core-concepts/memory-types)
5. [mem0 AI memory layer guide](https://mem0.ai/blog/ai-memory-layer-guide)
6. [mem0 LLM summarization guide 2025](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025)
7. [claude-mem GitHub repository](https://github.com/thedotmack/claude-mem)
8. [claude-mem Stop hook infinite loop — issue #987](https://github.com/thedotmack/claude-mem/issues/987)
9. [claude-mem SessionStart error — issue #1181](https://github.com/thedotmack/claude-mem/issues/1181)
10. [paperclipped.de claude-mem write-up](https://www.paperclipped.de/en/blog/claude-mem-persistent-memory-ai-coding-agents/)
11. [Generative Agents — arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
12. [Portkey Generative Agents summary](https://portkey.ai/blog/generative-agents-interactive-simulacra-of-human-behavior-summary/)
13. [claude-flow Agent System Overview wiki](https://github.com/ruvnet/claude-flow/wiki/Agent-System-Overview)
14. [Anthropic memory tool official docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
15. [Anthropic managed agents engineering post](https://www.anthropic.com/engineering/managed-agents)
16. [OpenAI workspace agents announcement](https://openai.com/index/introducing-workspace-agents-in-chatgpt/)
17. [VentureBeat workspace agents](https://venturebeat.com/orchestration/openai-unveils-workspace-agents-a-successor-to-custom-gpts-for-enterprises-that-can-plug-directly-into-slack-salesforce-and-more)
18. [JetBrains Research — efficient context management Dec 2025](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)
19. [Zylos AI compaction strategies Feb 2026](https://zylos.ai/research/2026-02-28-ai-agent-context-compression-strategies)

---

## Key learnings (flagged by L0 research)

- **claude-mem Stop hook infinite-loop (issue #987) is a critical architectural constraint.** Any hook that returns text containing imperative language or "next steps" phrasing to Claude's context will be interpreted as new work directives, preventing clean session termination. The safe pattern is write-to-disk only and return empty output to Claude. This MUST inform our `precompact_hook.py` extension and any future Stop-hook work.
- **JetBrains observation-masking outperforms LLM summarization for compaction** (SWE-bench Verified, Dec 2025). Masking cuts costs ~52%; summarization causes agents to run 15% longer because summaries smooth over stop signals. Hybrid (mask first, summarize only at severe threshold) adds another 7-11% saving.
- **Anthropic's `memver_` immutable versioning pattern** (memory tool docs, Aug 2025): every write creates a version identified by `memver_` prefix that belongs to the store, survives memory deletion, and enables rollback via read-then-rewrite. Redact endpoint scrubs content while preserving audit metadata. Closest existing pattern to our audit trail requirement.
