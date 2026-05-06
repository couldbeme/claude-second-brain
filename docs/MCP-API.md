# Memory MCP Server — API Reference

7 tools for persistent knowledge management. Used by Claude Code via MCP stdio transport.

## Configuration

Environment variables:
| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_DB_GLOBAL` | `~/.claude/memory/memory.db` | SQLite database path |
| `LMS_EMBEDDING_URL` | `http://localhost:1234/v1/embeddings` | LM Studio embedding endpoint |
| `LMS_EMBEDDING_MODEL` | `text-embedding-nomic-embed-text-v1.5` | Embedding model name |

## Tools

### memory_save

Store a new memory with optional auto-embedding.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| content | string | yes | — | The knowledge to store |
| category | string | yes | — | One of: decision, pattern, error, solution, learning, context, rule, persona |
| summary | string | no | "" | One-line summary (auto-generated from first 100 chars if empty) |
| tags | list[str] | no | [] | Searchable tags |
| project | string | no | null | Project scope |
| importance | int | no | 5 | 1-10 (10=critical rules, 1=temporary notes) |
| visibility | string | no | "personal" | personal, team, or public |

**Returns**: JSON with status, id, category, importance, visibility, embedding status.
**Note**: `persona` and `user_model` categories force visibility to `personal` regardless of input.

### memory_search

Search using hybrid semantic + keyword search (70% vector similarity + 30% BM25).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | yes | — | Search query |
| category | string | no | null | Filter by category |
| project | string | no | null | Filter by project |
| tags | list[str] | no | null | Filter by tags |
| limit | int | no | 5 | Max results |
| min_importance | int | no | null | Minimum importance threshold |

**Returns**: JSON with query, count, search_mode (hybrid/keyword-only), results array.
**Fallback**: If LM Studio is unavailable, falls back to keyword-only search via FTS5.

### memory_update

Update an existing memory. Re-embeds if content changes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| id | string | yes | — | Memory ID to update |
| content | string | no | null | New content (triggers re-embedding) |
| summary | string | no | null | New summary |
| tags | list[str] | no | null | New tags |
| importance | int | no | null | New importance |
| category | string | no | null | New category |
| visibility | string | no | null | New visibility |

**Returns**: JSON with status (updated/not_found), id.
**Note**: Changing category to persona/user_model forces visibility to personal.

### memory_delete

Permanently delete a memory. Requires explicit confirmation.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| id | string | yes | — | Memory ID to delete |
| confirm | bool | no | false | Must be true to proceed |

**Returns**: JSON with status (deleted/not_found/rejected), id.

### memory_list

Browse memories with optional filters.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| category | string | no | null | Filter by category |
| project | string | no | null | Filter by project |
| visibility | string | no | null | Filter: personal, team, or public |
| limit | int | no | 20 | Max results |
| offset | int | no | 0 | Pagination offset |
| sort_by | string | no | "updated_at" | Sort field: updated_at, created_at, importance, access_count |
| sort_order | string | no | "desc" | ASC or DESC |

**Returns**: JSON with count, compact results (id, category, summary, importance, project, updated_at).

### memory_get

Get full details of a specific memory. Increments access count.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| id | string | yes | — | Memory ID |

**Returns**: Full memory object (id, content, summary, category, project, tags, source, importance, access_count, created_at, updated_at, visibility) or not_found.

### memory_context

Load relevant context for the current task. Combines rules, task-relevant memories, and project context.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| task_description | string | yes | — | Description of current task |
| project | string | no | null | Project to scope search |
| include_rules | bool | no | true | Include rule-category memories |
| max_tokens | int | no | 2000 | Token budget for context block |

**Returns**: JSON with task, structured context block, rules_loaded flag, project.

## Security

- Content sanitization: strips markdown headings, flags jailbreak prefixes, truncates to 200 chars
- Visibility enforcement: persona/user_model always personal (defense-in-depth)
- Export scope: `--scope team` excludes personal visibility + personal-only categories

## Stack

| Component | Technology |
|-----------|-----------|
| Database | SQLite + sqlite-vec (vector search) + FTS5 (keyword search) |
| Embeddings | LM Studio + nomic-embed-text-v1.5 (768 dimensions) |
| MCP framework | FastMCP (Python, stdio transport) |
| Search ranking | 70% vector similarity + 30% BM25 keyword relevance |
