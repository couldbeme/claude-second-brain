"""Database layer for the memory system using SQLite + sqlite-vec + FTS5."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from typing import Optional

import sqlite_vec


EMBEDDING_DIM = 768


def _generate_id() -> str:
    return secrets.token_hex(8)


class MemoryDB:
    """SQLite-backed memory store with vector search and full-text search."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                summary TEXT,
                category TEXT NOT NULL,
                project TEXT,
                tags TEXT DEFAULT '[]',
                source TEXT DEFAULT 'manual',
                session_id TEXT,
                importance INTEGER DEFAULT 5,
                access_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT,
                superseded_by TEXT,
                FOREIGN KEY (superseded_by) REFERENCES memories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at DESC);
        """)

        # Create FTS5 table if not exists
        existing = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_fts'"
        ).fetchone()
        if not existing:
            self.conn.execute("""
                CREATE VIRTUAL TABLE memory_fts USING fts5(
                    content, summary, tags, category,
                    content='memories',
                    content_rowid='rowid'
                )
            """)

        # Create vector table if not exists
        existing = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_vectors'"
        ).fetchone()
        if not existing:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE memory_vectors USING vec0(embedding float[{EMBEDDING_DIM}])"
            )

        # Create links table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (from_id, to_id),
                FOREIGN KEY (from_id) REFERENCES memories(id),
                FOREIGN KEY (to_id) REFERENCES memories(id)
            )
        """)
        self.conn.commit()

    def save(
        self,
        content: str,
        category: str,
        summary: Optional[str] = None,
        tags: Optional[list[str]] = None,
        project: Optional[str] = None,
        importance: int = 5,
        source: str = "manual",
        session_id: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ) -> str:
        """Save a memory and return its ID."""
        mem_id = _generate_id()
        tags_json = json.dumps(tags or [])

        self.conn.execute(
            """INSERT INTO memories (id, content, summary, category, project, tags, source, session_id, importance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mem_id, content, summary, category, project, tags_json, source, session_id, importance),
        )

        # Get the rowid for FTS and vector indexing
        rowid = self.conn.execute(
            "SELECT rowid FROM memories WHERE id = ?", (mem_id,)
        ).fetchone()[0]

        # Index in FTS
        self.conn.execute(
            "INSERT INTO memory_fts(rowid, content, summary, tags, category) VALUES (?, ?, ?, ?, ?)",
            (rowid, content, summary or "", tags_json, category),
        )

        # Store embedding if provided
        if embedding is not None:
            self.conn.execute(
                "INSERT INTO memory_vectors(rowid, embedding) VALUES (?, ?)",
                (rowid, json.dumps(embedding)),
            )

        self.conn.commit()
        return mem_id

    def get(self, mem_id: str) -> Optional[dict]:
        """Get a memory by ID. Increments access_count."""
        row = self.conn.execute(
            """SELECT id, content, summary, category, project, tags, source,
                      importance, access_count, created_at, updated_at
               FROM memories WHERE id = ?""",
            (mem_id,),
        ).fetchone()

        if row is None:
            return None

        # Increment access count
        self.conn.execute(
            "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
            (mem_id,),
        )
        self.conn.commit()

        return {
            "id": row[0],
            "content": row[1],
            "summary": row[2],
            "category": row[3],
            "project": row[4],
            "tags": json.loads(row[5]) if row[5] else [],
            "source": row[6],
            "importance": row[7],
            "access_count": row[8] + 1,  # Reflect the increment
            "created_at": row[9],
            "updated_at": row[10],
        }

    def delete(self, mem_id: str) -> bool:
        """Delete a memory. Returns True if deleted, False if not found."""
        rowid = self.conn.execute(
            "SELECT rowid FROM memories WHERE id = ?", (mem_id,)
        ).fetchone()

        if rowid is None:
            return False

        rowid = rowid[0]

        # Delete from FTS
        self.conn.execute(
            "INSERT INTO memory_fts(memory_fts, rowid, content, summary, tags, category) "
            "SELECT 'delete', ?, content, summary, tags, category FROM memories WHERE id = ?",
            (rowid, mem_id),
        )

        # Delete from vectors (ignore if not exists)
        try:
            self.conn.execute("DELETE FROM memory_vectors WHERE rowid = ?", (rowid,))
        except sqlite3.OperationalError:
            pass

        # Delete from links
        self.conn.execute("DELETE FROM memory_links WHERE from_id = ? OR to_id = ?", (mem_id, mem_id))

        # Delete the memory itself
        self.conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        self.conn.commit()
        return True

    def update(
        self,
        mem_id: str,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[list[str]] = None,
        importance: Optional[int] = None,
        category: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ) -> bool:
        """Update a memory. Returns True if updated, False if not found."""
        existing = self.conn.execute(
            "SELECT rowid, content, summary, tags, category FROM memories WHERE id = ?",
            (mem_id,),
        ).fetchone()

        if existing is None:
            return False

        rowid = existing[0]
        old_content = existing[1]
        old_summary = existing[2]
        old_tags = existing[3]
        old_category = existing[4]

        # Delete old FTS entry
        self.conn.execute(
            "INSERT INTO memory_fts(memory_fts, rowid, content, summary, tags, category) "
            "VALUES ('delete', ?, ?, ?, ?, ?)",
            (rowid, old_content, old_summary or "", old_tags, old_category),
        )

        # Build update
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if category is not None:
            updates.append("category = ?")
            params.append(category)

        updates.append("updated_at = datetime('now')")
        params.append(mem_id)

        self.conn.execute(
            f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
            params,
        )

        # Re-index FTS with current values
        row = self.conn.execute(
            "SELECT content, summary, tags, category FROM memories WHERE id = ?",
            (mem_id,),
        ).fetchone()
        self.conn.execute(
            "INSERT INTO memory_fts(rowid, content, summary, tags, category) VALUES (?, ?, ?, ?, ?)",
            (rowid, row[0], row[1] or "", row[2], row[3]),
        )

        # Update embedding if provided
        if embedding is not None:
            try:
                self.conn.execute("DELETE FROM memory_vectors WHERE rowid = ?", (rowid,))
            except sqlite3.OperationalError:
                pass
            self.conn.execute(
                "INSERT INTO memory_vectors(rowid, embedding) VALUES (?, ?)",
                (rowid, json.dumps(embedding)),
            )

        self.conn.commit()
        return True

    def list_memories(
        self,
        category: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> list[dict]:
        """List memories with optional filters."""
        allowed_sort = {"updated_at", "created_at", "importance", "access_count"}
        if sort_by not in allowed_sort:
            sort_by = "updated_at"
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        conditions = []
        params = []
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if project is not None:
            conditions.append("project = ?")
            params.append(project)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, content, summary, category, project, tags, importance, access_count, updated_at
            FROM memories {where}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.conn.execute(query, params).fetchall()
        return [
            {
                "id": r[0],
                "content": r[1],
                "summary": r[2],
                "category": r[3],
                "project": r[4],
                "tags": json.loads(r[5]) if r[5] else [],
                "importance": r[6],
                "access_count": r[7],
                "updated_at": r[8],
            }
            for r in rows
        ]

    def keyword_search(self, query: str, limit: int = 10) -> list[dict]:
        """Search using FTS5 full-text search. Returns results with BM25 scores."""
        # Strip double quotes (they break FTS5 phrase queries) and bail on empty
        safe_query = query.replace('"', ' ').strip()
        if not safe_query:
            return []
        try:
            rows = self.conn.execute(
                """SELECT m.id, m.content, m.summary, m.category, m.project, m.tags,
                          m.importance, bm25(memory_fts) as score
                   FROM memory_fts f
                   JOIN memories m ON f.rowid = m.rowid
                   WHERE memory_fts MATCH ?
                   ORDER BY score
                   LIMIT ?""",
                (f'"{safe_query}"', limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            {
                "id": r[0],
                "content": r[1],
                "summary": r[2],
                "category": r[3],
                "project": r[4],
                "tags": json.loads(r[5]) if r[5] else [],
                "importance": r[6],
                "score": r[7],
            }
            for r in rows
        ]

    def vector_search(
        self, query_embedding: list[float], limit: int = 5
    ) -> list[dict]:
        """Search using vector similarity (L2 distance via sqlite-vec)."""
        try:
            rows = self.conn.execute(
                """SELECT v.rowid, v.distance, m.id, m.content, m.summary, m.category,
                          m.project, m.tags, m.importance
                   FROM memory_vectors v
                   JOIN memories m ON v.rowid = m.rowid
                   WHERE v.embedding MATCH ?
                     AND k = ?""",
                (json.dumps(query_embedding), limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            {
                "rowid": r[0],
                "distance": r[1],
                "id": r[2],
                "content": r[3],
                "summary": r[4],
                "category": r[5],
                "project": r[6],
                "tags": json.loads(r[7]) if r[7] else [],
                "importance": r[8],
            }
            for r in rows
        ]

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self) -> "MemoryDB":
        """Support use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the database connection on context manager exit."""
        self.close()
