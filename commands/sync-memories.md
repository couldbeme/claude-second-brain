---
description: Export or import memories for syncing between machines via git
argument-hint: "export" or "import"
---

# Sync Memories Between Machines

Export memories as JSON (committed to git) or import from JSON into the local database.

## Input

Action: $ARGUMENTS (must be "export" or "import")

## Export Workflow

1. Use `memory_list` with limit=1000 to get all memories.
2. For each memory, use `memory_get` to retrieve full details.
3. Write all memories as a JSON array to `memory/memories-export.json` with this structure:
   ```json
   [
     {
       "id": "abc123",
       "content": "...",
       "summary": "...",
       "category": "learning",
       "project": null,
       "tags": ["python"],
       "importance": 7,
       "source": "manual",
       "created_at": "2025-01-01 00:00:00",
       "updated_at": "2025-01-01 00:00:00"
     }
   ]
   ```
4. Report: how many memories exported.
5. Remind user to commit and push:
   ```
   git add memory/memories-export.json && git commit -m "sync: export memories" && git push
   ```

## Import Workflow

1. Check that `memory/memories-export.json` exists (user should have pulled from git first).
2. Read the JSON file.
3. For each memory in the file:
   - Check if a memory with the same `id` already exists (use `memory_get`).
   - If it exists AND `updated_at` in the file is newer: use `memory_update` to update it.
   - If it exists AND `updated_at` is the same or older: skip (local is current).
   - If it does not exist: save it with the original category, tags, importance.
4. Report: how many imported, how many skipped (already current), how many updated.

## Rules

- Never overwrite a newer local memory with an older export.
- Preserve original IDs during import so references stay consistent.
- The export file is safe to commit -- it contains no secrets (only knowledge you explicitly saved).
