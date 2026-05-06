"""Comprehensive tests for memory-mcp/db.py — real-DB coverage of MemoryDB.

Backfills the public-method coverage gap left by tests/test_code_quality_fixes.py
(which covers vector_search error handling, context manager, and list_memories
sort safety only).

Block 1  — TestSchemaMigration         (__init__ table + index + additive ALTER)
Block 2  — TestSaveHappyPath            (insert + FTS index + return id)
Block 3  — TestSaveValidation           (visibility allowlist, confidence clamp)
Block 4  — TestSavePersonalOnlyForcing  (persona/user_model categories)
Block 5  — TestSaveEmbedding            (vector table populated when embedding given)
Block 6  — TestSaveCustomMemId          (preserve passed-in id)
Block 7  — TestGet                       (happy, miss, access_count increment)
Block 8  — TestDelete                    (happy, miss, FTS+vector cleanup)
Block 9  — TestUpdateBasicFields         (each updatable field)
Block 10 — TestUpdatePersonalOnlyForce  (category change forces visibility)
Block 11 — TestUpdateMiss                (update on missing id returns False)
Block 12 — TestListMemoriesFiltering    (category/project/visibility filters)
Block 13 — TestListMemoriesPagination   (limit + offset)
Block 14 — TestKeywordSearch             (FTS5 happy + miss + special chars)
Block 15 — TestVectorSearchHappy         (real-vec round-trip)
Block 16 — TestContradictionDetection    (inversion pair + qualifier skip + no-tags)
Block 17 — TestGetContradictions         (happy + miss)
Block 18 — TestClose                     (idempotent close)
Block 19 — TestGenerateId                (16-char hex)
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Add memory-mcp/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import MemoryDB, _generate_id, EMBEDDING_DIM  # noqa: E402


def _new_db() -> tuple[MemoryDB, tempfile.TemporaryDirectory]:
    """Open a real MemoryDB on a temp file. Caller cleans up the TempDir."""
    tmp = tempfile.TemporaryDirectory()
    db_path = str(Path(tmp.name) / "test.db")
    return MemoryDB(db_path), tmp


def _embedding(seed: float = 0.1) -> list[float]:
    return [seed] * EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Block 1: TestSchemaMigration
# ---------------------------------------------------------------------------

class TestSchemaMigration(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_memories_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_required_columns_present(self):
        cols = {row[1] for row in self.db.conn.execute("PRAGMA table_info(memories)").fetchall()}
        required = {"id", "content", "category", "visibility", "confidence",
                    "valid_time", "transaction_time", "importance", "created_at"}
        self.assertTrue(required.issubset(cols), f"missing columns: {required - cols}")

    def test_fts_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='memory_fts'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_vector_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='memory_vectors'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_session_threads_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='session_threads'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_contradictions_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='contradictions'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_feedback_violations_table_created(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='feedback_violations'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_indexes_present(self):
        idx = {row[0] for row in self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()}
        # Spot-check critical indexes
        self.assertIn("idx_memories_category", idx)
        self.assertIn("idx_memories_visibility", idx)

    def test_init_idempotent(self):
        # Reopening the same DB should not raise or duplicate tables
        path = self.db.db_path
        self.db.close()
        db2 = MemoryDB(path)
        self.assertEqual(db2.db_path, path)
        db2.close()


# ---------------------------------------------------------------------------
# Block 2: TestSaveHappyPath
# ---------------------------------------------------------------------------

class TestSaveHappyPath(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_save_returns_id(self):
        mem_id = self.db.save("hello world", category="note")
        self.assertIsInstance(mem_id, str)
        self.assertEqual(len(mem_id), 16)

    def test_save_persists_row(self):
        mem_id = self.db.save("persistent text", category="learning")
        row = self.db.get(mem_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["content"], "persistent text")
        self.assertEqual(row["category"], "learning")

    def test_save_indexes_in_fts(self):
        self.db.save("findable phrase about quantum mechanics", category="research")
        rows = self.db.conn.execute(
            "SELECT count(*) FROM memory_fts WHERE memory_fts MATCH 'quantum'"
        ).fetchone()
        self.assertGreater(rows[0], 0)

    def test_save_default_visibility_personal(self):
        mem_id = self.db.save("default vis", category="note")
        row = self.db.get(mem_id)
        self.assertEqual(row["visibility"], "personal")

    def test_save_with_tags(self):
        mem_id = self.db.save("tagged", category="note", tags=["alpha", "beta"])
        row = self.db.get(mem_id)
        self.assertEqual(row["tags"], ["alpha", "beta"])


# ---------------------------------------------------------------------------
# Block 3: TestSaveValidation
# ---------------------------------------------------------------------------

class TestSaveValidation(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_invalid_visibility_raises(self):
        with self.assertRaises(ValueError):
            self.db.save("x", category="note", visibility="public-but-typo")

    def test_confidence_clamps_low(self):
        mem_id = self.db.save("c", category="note", confidence=-0.5)
        row = self.db.get(mem_id)
        self.assertEqual(row["confidence"], 0.0)

    def test_confidence_clamps_high(self):
        mem_id = self.db.save("c", category="note", confidence=2.5)
        row = self.db.get(mem_id)
        self.assertEqual(row["confidence"], 1.0)

    def test_confidence_default(self):
        mem_id = self.db.save("c", category="note")
        row = self.db.get(mem_id)
        self.assertAlmostEqual(row["confidence"], 0.75)


# ---------------------------------------------------------------------------
# Block 4: TestSavePersonalOnlyForcing
# ---------------------------------------------------------------------------

class TestSavePersonalOnlyForcing(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_persona_category_forces_personal(self):
        mem_id = self.db.save("p", category="persona", visibility="public")
        row = self.db.get(mem_id)
        self.assertEqual(row["visibility"], "personal")

    def test_user_model_category_forces_personal(self):
        mem_id = self.db.save("u", category="user_model", visibility="team")
        row = self.db.get(mem_id)
        self.assertEqual(row["visibility"], "personal")

    def test_other_category_respects_visibility(self):
        mem_id = self.db.save("n", category="note", visibility="team")
        row = self.db.get(mem_id)
        self.assertEqual(row["visibility"], "team")


# ---------------------------------------------------------------------------
# Block 5: TestSaveEmbedding
# ---------------------------------------------------------------------------

class TestSaveEmbedding(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_embedding_stored(self):
        emb = _embedding(0.42)
        mem_id = self.db.save("with vector", category="note", embedding=emb)
        rowid = self.db.conn.execute(
            "SELECT rowid FROM memories WHERE id=?", (mem_id,)
        ).fetchone()[0]
        count = self.db.conn.execute(
            "SELECT count(*) FROM memory_vectors WHERE rowid=?", (rowid,)
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_no_embedding_no_vector_row(self):
        mem_id = self.db.save("no vector", category="note")
        rowid = self.db.conn.execute(
            "SELECT rowid FROM memories WHERE id=?", (mem_id,)
        ).fetchone()[0]
        count = self.db.conn.execute(
            "SELECT count(*) FROM memory_vectors WHERE rowid=?", (rowid,)
        ).fetchone()[0]
        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# Block 6: TestSaveCustomMemId
# ---------------------------------------------------------------------------

class TestSaveCustomMemId(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_custom_mem_id_preserved(self):
        custom = "deadbeefcafe1234"
        mem_id = self.db.save("imported", category="note", mem_id=custom)
        self.assertEqual(mem_id, custom)
        row = self.db.get(custom)
        self.assertIsNotNone(row)


# ---------------------------------------------------------------------------
# Block 7: TestGet
# ---------------------------------------------------------------------------

class TestGet(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_get_existing_returns_dict(self):
        mem_id = self.db.save("found", category="note")
        row = self.db.get(mem_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], mem_id)
        self.assertEqual(row["content"], "found")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.db.get("nonexistent"))

    def test_get_increments_access_count(self):
        mem_id = self.db.save("counted", category="note")
        first = self.db.get(mem_id)
        self.assertEqual(first["access_count"], 1)
        second = self.db.get(mem_id)
        self.assertEqual(second["access_count"], 2)


# ---------------------------------------------------------------------------
# Block 8: TestDelete
# ---------------------------------------------------------------------------

class TestDelete(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_delete_existing_returns_true(self):
        mem_id = self.db.save("deleteme", category="note")
        self.assertTrue(self.db.delete(mem_id))
        self.assertIsNone(self.db.get(mem_id))

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.db.delete("nonexistent"))

    def test_delete_removes_from_fts(self):
        mem_id = self.db.save("ephemeral phrase", category="note")
        self.db.delete(mem_id)
        rows = self.db.conn.execute(
            "SELECT count(*) FROM memory_fts WHERE memory_fts MATCH 'ephemeral'"
        ).fetchone()
        self.assertEqual(rows[0], 0)

    def test_delete_removes_vector(self):
        mem_id = self.db.save("v", category="note", embedding=_embedding())
        rowid = self.db.conn.execute(
            "SELECT rowid FROM memories WHERE id=?", (mem_id,)
        ).fetchone()[0]
        self.db.delete(mem_id)
        count = self.db.conn.execute(
            "SELECT count(*) FROM memory_vectors WHERE rowid=?", (rowid,)
        ).fetchone()[0]
        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# Block 9: TestUpdateBasicFields
# ---------------------------------------------------------------------------

class TestUpdateBasicFields(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()
        self.mem_id = self.db.save("original", category="note", tags=["t1"], importance=3)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_update_content(self):
        self.assertTrue(self.db.update(self.mem_id, content="changed"))
        self.assertEqual(self.db.get(self.mem_id)["content"], "changed")

    def test_update_summary(self):
        self.db.update(self.mem_id, summary="now has summary")
        self.assertEqual(self.db.get(self.mem_id)["summary"], "now has summary")

    def test_update_tags(self):
        self.db.update(self.mem_id, tags=["new", "tag", "set"])
        self.assertEqual(self.db.get(self.mem_id)["tags"], ["new", "tag", "set"])

    def test_update_importance(self):
        self.db.update(self.mem_id, importance=10)
        self.assertEqual(self.db.get(self.mem_id)["importance"], 10)

    def test_update_category(self):
        self.db.update(self.mem_id, category="learning")
        self.assertEqual(self.db.get(self.mem_id)["category"], "learning")

    def test_update_confidence_clamps(self):
        self.db.update(self.mem_id, confidence=5.0)
        self.assertEqual(self.db.get(self.mem_id)["confidence"], 1.0)
        self.db.update(self.mem_id, confidence=-1.0)
        self.assertEqual(self.db.get(self.mem_id)["confidence"], 0.0)

    def test_update_visibility(self):
        self.db.update(self.mem_id, visibility="team")
        self.assertEqual(self.db.get(self.mem_id)["visibility"], "team")


# ---------------------------------------------------------------------------
# Block 10: TestUpdatePersonalOnlyForce
# ---------------------------------------------------------------------------

class TestUpdatePersonalOnlyForce(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_update_to_persona_forces_personal(self):
        mem_id = self.db.save("x", category="note", visibility="public")
        self.db.update(mem_id, category="persona")
        self.assertEqual(self.db.get(mem_id)["visibility"], "personal")

    def test_update_existing_persona_keeps_personal(self):
        mem_id = self.db.save("u", category="user_model")
        # Try to flip visibility on an existing user_model — must stay personal
        self.db.update(mem_id, visibility="team")
        self.assertEqual(self.db.get(mem_id)["visibility"], "personal")


# ---------------------------------------------------------------------------
# Block 11: TestUpdateMiss
# ---------------------------------------------------------------------------

class TestUpdateMiss(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_update_missing_returns_false(self):
        self.assertFalse(self.db.update("nope", content="x"))


# ---------------------------------------------------------------------------
# Block 12: TestListMemoriesFiltering
# ---------------------------------------------------------------------------

class TestListMemoriesFiltering(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()
        self.db.save("a", category="cat1", project="proj1", visibility="personal")
        self.db.save("b", category="cat2", project="proj1", visibility="team")
        self.db.save("c", category="cat1", project="proj2", visibility="personal")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_filter_by_category(self):
        rows = self.db.list_memories(category="cat1")
        self.assertEqual(len(rows), 2)

    def test_filter_by_project(self):
        rows = self.db.list_memories(project="proj1")
        self.assertEqual(len(rows), 2)

    def test_filter_by_visibility(self):
        rows = self.db.list_memories(visibility="team")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "b")

    def test_combined_filters(self):
        rows = self.db.list_memories(category="cat1", project="proj1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "a")

    def test_no_filters_returns_all(self):
        rows = self.db.list_memories()
        self.assertEqual(len(rows), 3)


# ---------------------------------------------------------------------------
# Block 13: TestListMemoriesPagination
# ---------------------------------------------------------------------------

class TestListMemoriesPagination(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()
        for i in range(15):
            self.db.save(f"m{i}", category="note", importance=i)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_default_limit_caps(self):
        rows = self.db.list_memories(limit=10)
        self.assertEqual(len(rows), 10)

    def test_offset_skips(self):
        first = self.db.list_memories(limit=5, offset=0)
        next_page = self.db.list_memories(limit=5, offset=5)
        first_ids = {r["id"] for r in first}
        next_ids = {r["id"] for r in next_page}
        self.assertEqual(first_ids & next_ids, set())

    def test_sort_by_importance_desc(self):
        rows = self.db.list_memories(sort_by="importance", sort_order="desc", limit=15)
        importances = [r["importance"] for r in rows]
        self.assertEqual(importances, sorted(importances, reverse=True))


# ---------------------------------------------------------------------------
# Block 14: TestKeywordSearch
# ---------------------------------------------------------------------------

class TestKeywordSearch(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()
        self.db.save("rapid prototyping with python", category="note")
        self.db.save("typing systems in rust", category="note")
        self.db.save("algorithms in javascript", category="note")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_search_finds_substring(self):
        rows = self.db.keyword_search("python")
        self.assertEqual(len(rows), 1)
        self.assertIn("python", rows[0]["content"])

    def test_search_returns_multiple(self):
        rows = self.db.keyword_search("typing")
        self.assertGreaterEqual(len(rows), 1)

    def test_search_no_match(self):
        rows = self.db.keyword_search("nonexistentterm")
        self.assertEqual(rows, [])

    def test_search_strips_quotes(self):
        # Double quotes break FTS5 phrase queries — code strips them
        rows = self.db.keyword_search('"python"')
        self.assertEqual(len(rows), 1)

    def test_search_empty_string_returns_empty(self):
        self.assertEqual(self.db.keyword_search(""), [])
        self.assertEqual(self.db.keyword_search("   "), [])

    def test_search_includes_score(self):
        rows = self.db.keyword_search("python")
        self.assertIn("score", rows[0])


# ---------------------------------------------------------------------------
# Block 15: TestVectorSearchHappy
# ---------------------------------------------------------------------------

class TestVectorSearchHappy(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_vector_search_returns_nearest(self):
        # Save two memories with distinct embeddings
        id_a = self.db.save("a", category="note", embedding=_embedding(0.0))
        id_b = self.db.save("b", category="note", embedding=_embedding(1.0))

        # Query close to A
        rows = self.db.vector_search(_embedding(0.05), limit=2)
        self.assertEqual(len(rows), 2)
        # A should be ranked first (smaller distance)
        self.assertEqual(rows[0]["id"], id_a)

    def test_vector_search_respects_limit(self):
        for i in range(5):
            self.db.save(f"m{i}", category="note", embedding=_embedding(i * 0.1))
        rows = self.db.vector_search(_embedding(0.0), limit=3)
        self.assertEqual(len(rows), 3)


# ---------------------------------------------------------------------------
# Block 16: TestContradictionDetection
# ---------------------------------------------------------------------------

class TestContradictionDetection(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_inversion_pair_flagged(self):
        # First memory: feature is "always" enabled
        self.db.save("the feature is always enabled", category="note",
                     project="p", tags=["feature-x"])
        # Second memory: feature is "never" enabled — should flag
        new_id = self.db.save("the feature is never enabled", category="note",
                               project="p", tags=["feature-x"])
        contradicts = self.db.get_contradictions(new_id)
        self.assertEqual(len(contradicts), 1)

    def test_qualifier_skips_detection(self):
        self.db.save("feature is always enabled", category="note",
                     project="p", tags=["feature-x"])
        # "sometimes" qualifier → no contradiction
        new_id = self.db.save("feature is sometimes never enabled", category="note",
                               project="p", tags=["feature-x"])
        contradicts = self.db.get_contradictions(new_id)
        self.assertEqual(contradicts, [])

    def test_no_tags_no_detection(self):
        self.db.save("always works", category="note", project="p", tags=["x"])
        new_id = self.db.save("never works", category="note", project="p", tags=[])
        self.assertEqual(self.db.get_contradictions(new_id), [])

    def test_different_project_no_match(self):
        self.db.save("always", category="note", project="proj1", tags=["t"])
        new_id = self.db.save("never", category="note", project="proj2", tags=["t"])
        self.assertEqual(self.db.get_contradictions(new_id), [])


# ---------------------------------------------------------------------------
# Block 17: TestGetContradictions
# ---------------------------------------------------------------------------

class TestGetContradictions(unittest.TestCase):

    def setUp(self):
        self.db, self.tmp = _new_db()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_no_contradictions_returns_empty(self):
        mem_id = self.db.save("clean", category="note")
        self.assertEqual(self.db.get_contradictions(mem_id), [])

    def test_returns_other_id(self):
        a = self.db.save("always works", category="note",
                         project="p", tags=["feat"])
        b = self.db.save("never works", category="note",
                         project="p", tags=["feat"])
        # b should contradict a; both directions should resolve
        self.assertIn(a, self.db.get_contradictions(b))
        self.assertIn(b, self.db.get_contradictions(a))


# ---------------------------------------------------------------------------
# Block 18: TestClose
# ---------------------------------------------------------------------------

class TestClose(unittest.TestCase):

    def test_close_then_reopen_works(self):
        tmp = tempfile.TemporaryDirectory()
        path = str(Path(tmp.name) / "c.db")

        db1 = MemoryDB(path)
        mem_id = db1.save("persisted", category="note")
        db1.close()

        # Reopen — data should still be there
        db2 = MemoryDB(path)
        row = db2.get(mem_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["content"], "persisted")
        db2.close()

        tmp.cleanup()


# ---------------------------------------------------------------------------
# Block 19: TestGenerateId
# ---------------------------------------------------------------------------

class TestGenerateId(unittest.TestCase):

    def test_returns_16_hex_chars(self):
        id_ = _generate_id()
        self.assertEqual(len(id_), 16)
        # All hex
        int(id_, 16)  # raises if not hex

    def test_unique_across_calls(self):
        ids = {_generate_id() for _ in range(100)}
        self.assertEqual(len(ids), 100)


if __name__ == "__main__":
    unittest.main()
