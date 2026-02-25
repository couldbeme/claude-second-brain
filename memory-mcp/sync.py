"""Export and import memories for syncing between machines.

Usage:
    python sync.py export              # Export all memories to JSON
    python sync.py import              # Import from JSON, merging with local
    python sync.py export --pretty     # Human-readable JSON
    python sync.py stats               # Show sync status
    python sync.py scheduled           # Export + auto git commit (for cron/launchd)
    python sync.py scheduled --push    # Export + git commit + push
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import MemoryDB

DEFAULT_EXPORT_PATH = os.path.expanduser("~/.claude/memory/memories-export.json")
DEFAULT_DB_PATH = os.path.expanduser("~/.claude/memory/memory.db")


def export_memories(pretty: bool = False, db_path: str = DEFAULT_DB_PATH, export_path: str = DEFAULT_EXPORT_PATH) -> int:
    """Export all memories to JSON file. Returns the count of exported memories."""
    db = MemoryDB(db_path)
    memories = db.list_memories(limit=10000, sort_by="created_at", sort_order="asc")

    # Get full details for each memory
    full_memories = []
    for m in memories:
        full = db.get(m["id"])
        if full:
            # Remove access_count from export (local metric)
            full.pop("access_count", None)
            full_memories.append(full)

    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    with open(export_path, "w") as f:
        json.dump(full_memories, f, indent=2 if pretty else None, ensure_ascii=False)

    db.close()
    count = len(full_memories)
    print(f"Exported {count} memories to {export_path}")
    print(f"File size: {os.path.getsize(export_path):,} bytes")
    return count


def import_memories(db_path: str = DEFAULT_DB_PATH, export_path: str = DEFAULT_EXPORT_PATH) -> None:
    """Import memories from JSON, merging with local database."""
    if not os.path.exists(export_path):
        print(f"Export file not found: {export_path}")
        print("Export from another machine first, then copy the file here.")
        sys.exit(1)

    with open(export_path) as f:
        incoming = json.load(f)

    db = MemoryDB(db_path)

    created = 0
    updated = 0
    skipped = 0

    for mem in incoming:
        existing = db.get(mem["id"])

        if existing is None:
            # New memory -- create it
            db.save(
                content=mem["content"],
                category=mem["category"],
                summary=mem.get("summary"),
                tags=mem.get("tags", []),
                project=mem.get("project"),
                importance=mem.get("importance", 5),
                source=mem.get("source", "sync"),
            )
            created += 1
        else:
            # Existing -- check timestamps
            incoming_ts = mem.get("updated_at", "")
            local_ts = existing.get("updated_at", "")

            if incoming_ts > local_ts:
                # Incoming is newer -- update
                db.update(
                    mem_id=mem["id"],
                    content=mem["content"],
                    summary=mem.get("summary"),
                    tags=mem.get("tags"),
                    importance=mem.get("importance"),
                    category=mem.get("category"),
                )
                updated += 1
            else:
                skipped += 1

    db.close()
    print(f"Import complete:")
    print(f"  Created: {created}")
    print(f"  Updated: {updated} (incoming was newer)")
    print(f"  Skipped: {skipped} (local was current or newer)")


def show_stats(db_path: str = DEFAULT_DB_PATH, export_path: str = DEFAULT_EXPORT_PATH) -> None:
    """Show sync status."""
    db = MemoryDB(db_path)
    memories = db.list_memories(limit=10000)
    db.close()

    print(f"Local database: {len(memories)} memories")

    if os.path.exists(export_path):
        with open(export_path) as f:
            exported = json.load(f)
        mtime = datetime.fromtimestamp(os.path.getmtime(export_path))
        print(f"Export file: {len(exported)} memories (last exported: {mtime:%Y-%m-%d %H:%M})")

        local_ids = {m["id"] for m in memories}
        export_ids = {m["id"] for m in exported}
        only_local = local_ids - export_ids
        only_export = export_ids - local_ids

        if only_local:
            print(f"  Local-only (not exported): {len(only_local)}")
        if only_export:
            print(f"  Export-only (not imported): {len(only_export)}")
        if not only_local and not only_export:
            print("  In sync (same IDs)")
    else:
        print("Export file: not found (run 'python sync.py export' first)")


log = logging.getLogger("sync")


def scheduled_export(
    db_path: str = DEFAULT_DB_PATH,
    export_path: str = DEFAULT_EXPORT_PATH,
    push: bool = False,
) -> dict:
    """Export memories and auto-commit to git. Designed for cron/launchd.

    Returns a summary dict: {exported, committed, pushed, error}.
    Never raises — all errors are caught and returned in the dict.
    """
    result = {"exported": 0, "committed": False, "pushed": False, "error": None}

    try:
        # 1. Export
        result["exported"] = export_memories(
            db_path=db_path, export_path=export_path, pretty=True
        )

        # 2. Git add
        subprocess.run(
            ["git", "add", export_path],
            capture_output=True, text=True, check=True,
        )

        # 3. Check if there are staged changes
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet", export_path],
            capture_output=True, text=True,
        )
        if diff_result.returncode == 0:
            # No changes — nothing to commit
            log.info("No changes to commit")
            return result

        # 4. Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"sync: auto-export memories ({timestamp})"],
            capture_output=True, text=True, check=True,
        )
        result["committed"] = True

        # 5. Optional push
        if push:
            subprocess.run(
                ["git", "push"],
                capture_output=True, text=True, check=True,
            )
            result["pushed"] = True

    except Exception as e:
        log.error("Scheduled export failed: %s", e)
        result["error"] = str(e)

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "export":
        export_memories(pretty="--pretty" in sys.argv)
    elif cmd == "import":
        import_memories()
    elif cmd == "stats":
        show_stats()
    elif cmd == "scheduled":
        result = scheduled_export(push="--push" in sys.argv)
        if result["error"]:
            print(f"Error: {result['error']}")
            sys.exit(1)
        print(f"Exported: {result['exported']}, Committed: {result['committed']}, Pushed: {result['pushed']}")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
