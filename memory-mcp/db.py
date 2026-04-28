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

    # Categories that are always forced to 'personal' visibility
    PERSONAL_ONLY_CATEGORIES = ("persona", "user_model")
    VALID_VISIBILITIES = ("personal", "team", "public")

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
                visibility TEXT NOT NULL DEFAULT 'personal',
                confidence REAL DEFAULT 0.75,
                valid_time TEXT,
                transaction_time TEXT DEFAULT (datetime('now')),
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

        # Migration: add columns to existing tables as needed (additive-only, never DROP)
        columns = [
            row[1] for row in self.conn.execute("PRAGMA table_info(memories)").fetchall()
        ]
        if "visibility" not in columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN visibility TEXT NOT NULL DEFAULT 'personal'"
            )
        if "confidence" not in columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN confidence REAL DEFAULT 0.75"
            )
        if "valid_time" not in columns:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN valid_time TEXT"
            )
        if "transaction_time" not in columns:
            # SQLite ALTER TABLE does not support non-constant DEFAULT expressions.
            # Add the column with NULL default; new rows supply the value explicitly.
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN transaction_time TEXT"
            )
        self.conn.commit()

        # Create visibility index (after migration ensures column exists)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_visibility ON memories(visibility)"
        )
        self.conn.commit()

        # Contradictions table for drift detection
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contradictions (
                id TEXT PRIMARY KEY,
                memory_a_id TEXT NOT NULL,
                memory_b_id TEXT NOT NULL,
                detected_at TEXT DEFAULT (datetime('now')),
                resolution TEXT DEFAULT 'unresolved',
                FOREIGN KEY (memory_a_id) REFERENCES memories(id),
                FOREIGN KEY (memory_b_id) REFERENCES memories(id)
            )
        """)

        # Feedback violations table (MYTHOS-SUBSTRATE Phase 1) — behavioral
        # surprise detection: when current session activity matches a feedback
        # memory's trigger pattern, the system records the would-be slip.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_violations (
                id TEXT PRIMARY KEY,
                feedback_memory_id TEXT NOT NULL,
                matched_text TEXT NOT NULL,
                matched_pattern TEXT NOT NULL,
                session_id TEXT,
                detected_at TEXT DEFAULT (datetime('now')),
                resolution TEXT DEFAULT 'unresolved',
                FOREIGN KEY (feedback_memory_id) REFERENCES memories(id)
            )
        """)
        self.conn.commit()

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
        mem_id: Optional[str] = None,
        visibility: str = "personal",
        confidence: float = 0.75,
    ) -> str:
        """Save a memory and return its ID. Pass mem_id to preserve an existing ID (e.g. during import)."""
        if visibility not in self.VALID_VISIBILITIES:
            raise ValueError(
                f"visibility must be one of {self.VALID_VISIBILITIES}, got {visibility!r}"
            )
        mem_id = mem_id or _generate_id()
        tags_json = json.dumps(tags or [])
        confidence = max(0.0, min(1.0, confidence))

        # Force personal visibility for sensitive categories
        if category in self.PERSONAL_ONLY_CATEGORIES:
            visibility = "personal"

        self.conn.execute(
            """INSERT INTO memories
               (id, content, summary, category, project, tags, source, session_id,
                importance, visibility, confidence, transaction_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (mem_id, content, summary, category, project, tags_json, source, session_id,
             importance, visibility, confidence),
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

        # Contradiction detection (non-blocking)
        self._detect_contradictions(mem_id, content, project, tags or [])

        return mem_id

    def get(self, mem_id: str) -> Optional[dict]:
        """Get a memory by ID. Increments access_count."""
        row = self.conn.execute(
            """SELECT id, content, summary, category, project, tags, source,
                      importance, access_count, created_at, updated_at, visibility, confidence
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
            "visibility": row[11],
            "confidence": row[12] if row[12] is not None else 0.75,
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
        visibility: Optional[str] = None,
        confidence: Optional[float] = None,
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
        # Enforce personal-only for sensitive categories, even if visibility wasn't passed
        effective_cat = category or old_category
        if effective_cat in self.PERSONAL_ONLY_CATEGORIES:
            updates.append("visibility = ?")
            params.append("personal")
        elif visibility is not None:
            updates.append("visibility = ?")
            params.append(visibility)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(max(0.0, min(1.0, confidence)))

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
        visibility: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> list[dict]:
        """List memories with optional filters."""
        SORT_MAP = {
            "updated_at": "updated_at",
            "created_at": "created_at",
            "importance": "importance",
            "access_count": "access_count",
        }
        ORDER_MAP = {"asc": "ASC", "desc": "DESC"}
        safe_sort = SORT_MAP.get(sort_by, "updated_at")
        safe_order = ORDER_MAP.get(sort_order, "DESC")

        conditions = []
        params = []
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if project is not None:
            conditions.append("project = ?")
            params.append(project)
        if visibility is not None:
            conditions.append("visibility = ?")
            params.append(visibility)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, content, summary, category, project, tags, importance, access_count, updated_at, visibility, confidence
            FROM memories {where}
            ORDER BY {safe_sort} {safe_order}
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
                "visibility": r[9],
                "confidence": r[10] if r[10] is not None else 0.75,
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
                          m.importance, bm25(memory_fts) as score, m.confidence
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
                "confidence": r[8] if r[8] is not None else 0.75,
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
                          m.project, m.tags, m.importance, m.confidence
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
                "confidence": r[9] if r[9] is not None else 0.75,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Drift detection (v0.1, rule-based — no LLM)
    # ------------------------------------------------------------------

    # Inversion pairs: if new content has word A and candidate has word B (or vice-versa)
    # → flag as contradiction.
    _INVERSION_PAIRS: list[tuple[str, str]] = [
        ("always", "never"),
        ("yes", "no"),
        ("present", "absent"),
        ("exists", "missing"),
        ("works", "broken"),
        ("supported", "unsupported"),
        ("enabled", "disabled"),
        ("required", "optional"),
        ("true", "false"),
    ]

    # Qualifier words: if either text contains one → skip (soft contradiction)
    _QUALIFIERS: set[str] = {
        "maybe", "sometimes", "often", "partial", "partially", "mostly",
    }

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Lowercase-split text on non-word characters; return set of tokens."""
        import re
        return set(re.findall(r"[a-z]+", text.lower()))

    def _detect_contradictions(
        self,
        new_id: str,
        content: str,
        project: Optional[str],
        tags: list[str],
    ) -> list[str]:
        """
        Detect keyword-inversion contradictions between the new memory and recent
        memories in the same project with overlapping tags.

        Inserts rows into the `contradictions` table for each conflict found.
        Returns list of conflicting memory IDs (empty if none).
        """
        if not tags:
            return []

        new_tokens = self._tokenize(content)

        # Skip detection if new content has a qualifier word
        if new_tokens & self._QUALIFIERS:
            return []

        # Build tag-overlap condition (any tag in common)
        # We search raw JSON strings — good enough for v0.1
        tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
        tag_params: list = [f'%"{t}"%' for t in tags]

        # Project match: both NULL → match, both same value → match
        if project is None:
            project_condition = "project IS NULL"
            project_params: list = []
        else:
            project_condition = "project = ?"
            project_params = [project]

        query = f"""
            SELECT id, content FROM memories
            WHERE ({tag_conditions})
              AND {project_condition}
              AND transaction_time >= datetime('now', '-30 days')
              AND id != ?
        """
        params = tag_params + project_params + [new_id]

        try:
            candidates = self.conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            # transaction_time column may not exist on very old DBs
            return []

        conflicts: list[str] = []
        for (cand_id, cand_content) in candidates:
            cand_tokens = self._tokenize(cand_content)

            # Skip if candidate has a qualifier
            if cand_tokens & self._QUALIFIERS:
                continue

            # Check inversion pairs in both directions
            flagged = False
            for (word_a, word_b) in self._INVERSION_PAIRS:
                if (word_a in new_tokens and word_b in cand_tokens) or \
                   (word_b in new_tokens and word_a in cand_tokens):
                    flagged = True
                    break

            if flagged:
                contra_id = _generate_id()
                try:
                    self.conn.execute(
                        """INSERT INTO contradictions
                           (id, memory_a_id, memory_b_id)
                           VALUES (?, ?, ?)""",
                        (contra_id, cand_id, new_id),
                    )
                    self.conn.commit()
                except sqlite3.IntegrityError:
                    pass  # Duplicate; ignore
                conflicts.append(cand_id)

        return conflicts

    def get_contradictions(self, mem_id: str) -> list[str]:
        """
        Return list of memory IDs that are recorded as contradicting `mem_id`.

        Looks in both directions of the contradictions table.
        """
        rows = self.conn.execute(
            """SELECT memory_a_id, memory_b_id FROM contradictions
               WHERE memory_a_id = ? OR memory_b_id = ?""",
            (mem_id, mem_id),
        ).fetchall()

        result: list[str] = []
        for (a, b) in rows:
            other = b if a == mem_id else a
            result.append(other)
        return result

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self) -> "MemoryDB":
        """Support use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the database connection on context manager exit."""
        self.close()
