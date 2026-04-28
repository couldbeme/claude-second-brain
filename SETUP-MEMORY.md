# Memory System Setup Guide

The memory system is a core component of the toolkit. It gives Claude Code persistent knowledge across sessions, storing learnings, decisions, patterns, and context in a local SQLite database with hybrid search (semantic vectors + keyword matching).

## System Requirements

| Component | Requirement | Notes |
|-----------|------------|-------|
| Python | 3.10+ | For the MCP server |
| SQLite | 3.41+ | Needs FTS5 (built-in on macOS and most Linux) |
| Disk | ~500MB | LM Studio (~300MB) + embedding model (~270MB) + DB |
| RAM | ~2GB extra | When LM Studio is running the embedding model |
| OS | macOS, Linux | Windows: untested but should work via WSL |

**LM Studio is optional.** Without it, search falls back to keyword-only (BM25). You lose semantic similarity but the memory system remains fully functional. The memory system itself is required -- it powers `/learn`, `/recall`, self-learning, and context recovery.

## Setup Steps

### Step 1: Install LM Studio

Download from [lmstudio.ai](https://lmstudio.ai). It's a free local LLM runner with an OpenAI-compatible API.

### Step 2: Download the embedding model

1. Open LM Studio
2. Go to the **Search** tab
3. Search for `nomic-embed-text-v1.5`
4. Download `nomic-ai/nomic-embed-text-v1.5-GGUF`
5. Go to the **Developer** tab (or **Local Server** in older versions)
6. Load the model
7. Start the server (default: `http://localhost:1234`)

Verify it's working:
```bash
curl http://localhost:1234/v1/models
# Should return a JSON response listing the loaded model
```

### Step 3: Set up the MCP server

```bash
# From the toolkit root
cd memory-mcp

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Verify it works
python server.py --health-check
# Should print: "Memory MCP server OK"
```

### Step 4: Configure Claude Code

Add the memory MCP server to your `~/.claude/settings.json`. If the file doesn't exist, create it.

```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "/full/path/to/memory-mcp/.venv/bin/python3",
      "args": ["/full/path/to/memory-mcp/server.py"],
      "env": {
        "MEMORY_DB_GLOBAL": "/full/path/to/.claude/memory/memory.db",
        "LMS_EMBEDDING_URL": "http://localhost:1234/v1/embeddings",
        "LMS_EMBEDDING_MODEL": "text-embedding-nomic-embed-text-v1.5"
      }
    }
  }
}
```

**Important:** Replace `/full/path/to/` with actual absolute paths. A template is provided at `memory-mcp/settings.json.template`.

Example for macOS:
```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "/Users/yourname/.claude/memory-mcp/.venv/bin/python3",
      "args": ["/Users/yourname/.claude/memory-mcp/server.py"],
      "env": {
        "MEMORY_DB_GLOBAL": "/Users/yourname/.claude/memory/memory.db",
        "LMS_EMBEDDING_URL": "http://localhost:1234/v1/embeddings",
        "LMS_EMBEDDING_MODEL": "text-embedding-nomic-embed-text-v1.5"
      }
    }
  }
}
```

### Step 5: Restart Claude Code

Restart Claude Code (or start a new session). The memory tools should now be available. Test it:

```
# In Claude Code, type:
Save a test memory about this project using the memory tools

# Then search for it:
Search my memories for "test"
```

### Step 6: Enable the continuity layer (optional but recommended)

The continuity layer captures structural session state (decisions, in-flight tasks, open threads) so a post-`/compact` session can re-orient via `/resume` instead of losing context. Two pieces:

**6a. PreCompact hook** — already wired into the `settings.json.template` from Step 4. If you copied that template, the hook is registered. To verify:

```bash
grep -A 6 PreCompact ~/.claude/settings.json
```

You should see a hooks block pointing to `precompact_hook.py`.

**6b. Bridge journal trigger rule** — add the following to your `~/.claude/CLAUDE.md` Non-Negotiable Rules so Claude knows when to log structural entries to `session_bridge.md` during a session. Without this, the journal stays empty and the continuity snapshot has nothing to capture.

```markdown
**Session-bridge logging.** During a session, write structural entries to
`session_bridge.md` via the bridge CLI as triggering events fire. Invocation:

```bash
REPLACE_WITH_TOOLKIT_PATH/memory-mcp/.venv/bin/python3 \
  REPLACE_WITH_TOOLKIT_PATH/memory-mcp/bridge_append.py <TYPE> "<payload>"
```

Trigger taxonomy (manual triggers — payload is structural metadata only,
NEVER message-body verbatim):

| Type | Fire when | Payload format |
|---|---|---|
| `DECISION` | A non-trivial decision lands | `<text> \| WHY: <rationale> \| REJECTED: <alt>` |
| `INFLIGHT` | On agent dispatch / major sub-step transition | `task=<text> \| step=<text> \| next=<text>` |
| `THREAD-OPEN` | Flag an unresolved branch | `<8-hex-id> \| <description>` |
| `THREAD-CLOSE` | Branch resolves | `<8-hex-id>` |

The CLI caps payloads at 500 chars and strips newlines. Calls are
fire-and-forget — exit code is not checked.
```

**6c. Privacy gitignore** — add these lines to `~/.claude/.gitignore` to keep the bridge journal and continuity snapshots out of any private dotfiles backup:

```
projects/*/memory/continuity_pre_compact_*.md
projects/*/memory/session_bridge.md
projects/*/memory/session_bridge_*.md
```

After this setup, every `/compact` writes a `continuity_pre_compact_<session_id>.md` snapshot to your per-project memory dir, and `/resume` reads it on the next session start.

## Available Memory Tools

Once configured, Claude Code gets 7 new tools:

| Tool | What it does |
|------|-------------|
| `memory_save` | Store a piece of knowledge (with auto-embedding) |
| `memory_search` | Hybrid semantic + keyword search |
| `memory_get` | Retrieve a specific memory by ID |
| `memory_update` | Update an existing memory (re-embeds automatically) |
| `memory_delete` | Permanently delete a memory |
| `memory_list` | List memories with filters (category, project, importance) |
| `memory_context` | Load relevant context for a task (rules + related memories) |

## How It Works

```
Your prompt
    |
    v
memory_save("rate limiting uses sliding window")
    |
    ├── Generate 768-dim embedding via LM Studio
    |
    └── Store in SQLite
         ├── memories table (content, metadata)
         ├── memory_vectors (sqlite-vec, 768-dim)
         └── memory_fts (FTS5, BM25 keyword index)

memory_search("how do we handle rate limits?")
    |
    ├── Vector search (70% weight) -- semantic similarity
    ├── Keyword search (30% weight) -- BM25 relevance
    └── Combined, ranked, filtered
```

## Troubleshooting

### "Embedding service unavailable"
- LM Studio isn't running, or the model isn't loaded
- Check: `curl http://localhost:1234/v1/models`
- The system still works (keyword-only search), but semantic search is disabled

### "sqlite-vec not found" or extension loading errors
- Reinstall: `pip install sqlite-vec>=0.1.6`
- On some systems, you may need to compile SQLite with extension loading enabled

### Memory tools not appearing in Claude Code
- Check `~/.claude/settings.json` has the correct paths
- Verify: `python memory-mcp/server.py --health-check`
- Restart Claude Code after changing settings.json

### Database is empty after restart
- Normal -- the database persists at the path in `MEMORY_DB_GLOBAL`
- Check the path exists: `ls ~/.claude/memory/memory.db`
- The DB is created automatically on first save

## Automated Sync

The memory system supports automated periodic exports that commit to git. This ensures your knowledge base is backed up and available across machines without manual intervention.

### Quick Setup (cron)

```bash
# Export every hour, auto-commit to git
crontab -e
# Add this line:
0 * * * * /path/to/.venv/bin/python3 /path/to/memory-mcp/sync.py scheduled 2>&1 >> ~/.claude/memory/sync.log
```

### macOS Setup (launchd) -- recommended

```bash
# 1. Copy the template
cp memory-mcp/com.claude.sync-memories.plist.template \
   ~/Library/LaunchAgents/com.claude.sync-memories.plist

# 2. Edit and replace REPLACE_WITH_* placeholders with actual paths

# 3. Load it
launchctl load ~/Library/LaunchAgents/com.claude.sync-memories.plist

# 4. Verify
launchctl list | grep claude
```

### How it works

1. Exports all memories to `~/.claude/memory/memories-export.json`
2. Runs `git add` on the export file
3. If there are changes, commits with a timestamped message
4. With `--push` flag, also pushes to remote after commit
5. Safe for cron/launchd: errors are logged, never crash

### Commands

```bash
python sync.py scheduled           # export + git commit
python sync.py scheduled --push    # export + git commit + push
```

### Verify it works

```bash
# Manual test
cd /path/to/memory-mcp && python sync.py scheduled
# Check the log
cat ~/.claude/memory/sync.log
# Check git log
git log --oneline -3
```

## Recommended Workflow

1. **Start LM Studio** at the beginning of your work session (or set it to auto-start)
2. **Use `/learn`** after discoveries: `[LEARNING]` tags get saved automatically
3. **Use `/recall`** before starting work on something familiar
4. **Set up automated sync** (see above) -- no more manual exports
5. If LM Studio isn't running, everything still works -- just without semantic search
