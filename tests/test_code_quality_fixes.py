"""TDD tests for 5 code quality fixes across hybrid_search.py, db.py, and sync.py.

Covers:
1. min_importance=0 truthiness bug in hybrid_search
2. vector_search missing try/except in db
3. MemoryDB context manager support (__enter__/__exit__)
4. File handle leak in export_memories (with-statement)
5. JSON error handling in import_memories
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Add memory-mcp to path
MEMORY_MCP = str(Path(__file__).parent.parent / "memory-mcp")
if MEMORY_MCP not in sys.path:
    sys.path.insert(0, MEMORY_MCP)

# Ensure sqlite_vec is mocked (it's a native extension not available in test env).
# Also forcibly remove any prior MagicMock stubs for db/hybrid_search/sync so
# that we import the real modules (test_sync_scheduled.py sets those stubs at
# module level, which would otherwise pollute this file when pytest collects
# both files in the same process).
sys.modules["sqlite_vec"] = MagicMock()
for _mod in ("db", "hybrid_search", "sync"):
    sys.modules.pop(_mod, None)

import importlib
import db as _real_db          # load real db (with sqlite_vec mocked)
import hybrid_search as _real_hs  # load real hybrid_search
import sync as _real_sync      # load real sync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(importance: int, **kwargs) -> dict:
    """Return a minimal memory dict for use in hybrid_search result lists."""
    defaults = {
        "id": "abc123",
        "content": "test content",
        "summary": None,
        "category": "test",
        "project": None,
        "tags": [],
        "importance": importance,
        "score": 0.5,
        "vector_score": 0.5,
        "keyword_score": 0.5,
    }
    defaults.update(kwargs)
    return defaults


# ===========================================================================
# Fix 1: min_importance=0 truthiness bug in hybrid_search
# ===========================================================================

class TestMinImportanceTruthiness:
    """min_importance=0 must still apply the filter (0 is falsy in Python)."""

    def _run_search(self, min_importance, memories):
        """Import hybrid_search fresh and patch its DB calls."""
        # Import here so sys.path manipulation above takes effect
        import importlib
        import hybrid_search as hs

        mock_db = MagicMock()
        mock_db.vector_search.return_value = []
        # Return memories via keyword_search
        mock_db.keyword_search.return_value = [
            {**m, "score": -1.0} for m in memories
        ]

        return hs.hybrid_search(
            db=mock_db,
            query="test",
            query_embedding=None,
            limit=10,
            min_importance=min_importance,
        )

    def test_min_importance_zero_filters_nothing_out_when_all_qualify(self):
        """min_importance=0 keeps all memories (importance >= 0 is always true)."""
        memories = [
            _make_memory(importance=0, id="mem_zero"),
            _make_memory(importance=5, id="mem_five"),
        ]
        results = self._run_search(min_importance=0, memories=memories)
        assert len(results) == 2, (
            "min_importance=0 should keep all memories since importance >= 0 always. "
            f"Got {len(results)} results: {[r['id'] for r in results]}"
        )

    def test_min_importance_zero_does_not_skip_filter(self):
        """When min_importance=0, filter is applied (items with importance >= 0 pass)."""
        # With the bug: if min_importance=0, the `if min_importance:` branch is
        # skipped so NO filtering occurs. With the fix: the branch runs but since
        # all importances >= 0, all items pass. The two cases produce the same
        # output here, so we need a case where 0 distinguishes buggy vs fixed code.
        #
        # The real distinguishing case: min_importance=0 with a non-zero value.
        # Both buggy and fixed code pass that. The bug only matters when some
        # items WOULD be filtered but 0 skips the filter. Let's test min_importance=1
        # with importance=0 items to confirm they ARE filtered (sanity check),
        # and then verify min_importance=0 keeps them.
        low_importance = _make_memory(importance=0)
        results = self._run_search(min_importance=0, memories=[low_importance])
        assert len(results) == 1, "importance=0 memory should pass min_importance=0 filter"

    def test_min_importance_one_filters_out_zero_importance(self):
        """min_importance=1 must exclude memories with importance=0."""
        memories = [
            _make_memory(importance=0, id="low"),
            _make_memory(importance=5, id="normal"),
        ]
        results = self._run_search(min_importance=1, memories=memories)
        ids = [r["id"] for r in results]
        assert "low" not in ids
        assert "normal" in ids

    def test_min_importance_none_applies_no_filter(self):
        """min_importance=None (default) applies no filter at all."""
        memories = [
            _make_memory(importance=0, id="zero"),
            _make_memory(importance=10, id="high"),
        ]
        results = self._run_search(min_importance=None, memories=memories)
        assert len(results) == 2

    def test_min_importance_zero_is_not_none(self):
        """Specifically: min_importance=0 MUST trigger filter branch (not None branch).

        This is the exact bug: `if min_importance:` treats 0 as falsy.
        We verify the correct condition by checking that importance=0 memories
        are NOT filtered out when min_importance=0.
        """
        memories = [
            _make_memory(importance=0, id="zero_imp"),
            _make_memory(importance=3, id="three_imp"),
        ]
        results = self._run_search(min_importance=0, memories=memories)
        ids = [r["id"] for r in results]
        # Both should survive since both have importance >= 0
        assert "zero_imp" in ids
        assert "three_imp" in ids

    def test_min_importance_zero_condition_uses_is_not_none(self):
        """Source must use `is not None` check, not bare truthiness, for min_importance.

        `if min_importance:` is falsy for 0, skipping the filter unintentionally.
        `if min_importance is not None:` is the correct guard.
        """
        import inspect
        import hybrid_search as hs

        source = inspect.getsource(hs.hybrid_search)
        assert "if min_importance is not None:" in source, (
            "hybrid_search uses `if min_importance:` which treats 0 as falsy. "
            "Must be `if min_importance is not None:` to correctly handle min_importance=0."
        )


# ===========================================================================
# Fix 2: vector_search missing try/except in db.py
# ===========================================================================

class TestVectorSearchErrorHandling:
    """vector_search should return [] on sqlite3.OperationalError, not raise."""

    def test_vector_search_returns_empty_on_operational_error(self):
        """sqlite3.OperationalError during vector search returns []."""
        import sqlite3
        import importlib
        import db as db_module

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("no such table: memory_vectors")

        mem_db = object.__new__(db_module.MemoryDB)
        mem_db.conn = mock_conn

        result = mem_db.vector_search([0.1] * 768, limit=5)

        assert result == [], (
            "vector_search should catch sqlite3.OperationalError and return [], "
            "matching the behaviour of keyword_search"
        )

    def test_vector_search_does_not_raise_on_operational_error(self):
        """No exception propagates out of vector_search on db error."""
        import sqlite3
        import db as db_module

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("vec0 not loaded")

        mem_db = object.__new__(db_module.MemoryDB)
        mem_db.conn = mock_conn

        try:
            mem_db.vector_search([0.0] * 768)
        except sqlite3.OperationalError:
            pytest.fail("vector_search must not propagate sqlite3.OperationalError")

    def test_vector_search_still_returns_results_when_no_error(self):
        """Normal vector search path still returns rows correctly."""
        import db as db_module

        fake_row = (1, 0.25, "mem_abc", "content here", "summary", "cat", "proj", '["tag"]', 7)
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [fake_row]

        mem_db = object.__new__(db_module.MemoryDB)
        mem_db.conn = mock_conn

        results = mem_db.vector_search([0.1] * 768, limit=5)

        assert len(results) == 1
        assert results[0]["id"] == "mem_abc"
        assert results[0]["distance"] == 0.25


# ===========================================================================
# Fix 3: MemoryDB context manager support
# ===========================================================================

class TestMemoryDBContextManager:
    """MemoryDB must support `with MemoryDB(...) as db:` usage.

    Tests bypass __init__ via object.__new__ to avoid the sqlite_vec
    dependency that requires the native extension at runtime.
    """

    def _make_mem_db(self):
        """Create a MemoryDB instance without calling __init__."""
        import db as db_module
        mem_db = object.__new__(db_module.MemoryDB)
        mem_db.conn = MagicMock()
        return mem_db

    def test_enter_returns_self(self):
        """__enter__ must return the MemoryDB instance."""
        mem_db = self._make_mem_db()
        result = mem_db.__enter__()
        assert result is mem_db

    def test_exit_calls_close(self):
        """__exit__ must call self.close()."""
        import db as db_module

        mem_db = self._make_mem_db()
        close_called = []
        # Patch close so we can track the call without a real connection
        mem_db.close = lambda: close_called.append(True)

        mem_db.__exit__(None, None, None)

        assert close_called, "__exit__ must call self.close()"

    def test_context_manager_protocol_present(self):
        """MemoryDB class must expose __enter__ and __exit__ methods."""
        import db as db_module

        assert hasattr(db_module.MemoryDB, "__enter__"), (
            "MemoryDB must define __enter__ to support `with` statement"
        )
        assert hasattr(db_module.MemoryDB, "__exit__"), (
            "MemoryDB must define __exit__ to support `with` statement"
        )

    def test_context_manager_with_statement_using_mocked_db(self):
        """Can use MemoryDB as a context manager; close is called on exit."""
        import db as db_module

        mem_db = self._make_mem_db()
        close_calls = []
        mem_db.close = lambda: close_calls.append(True)

        with mem_db as ctx:
            assert ctx is mem_db

        assert close_calls, "close() must be called when exiting the context manager"

    def test_exit_passes_through_exception(self):
        """__exit__ does not suppress exceptions raised in the with block."""
        mem_db = self._make_mem_db()
        mem_db.close = lambda: None  # no-op close

        with pytest.raises(ValueError, match="intentional"):
            with mem_db:
                raise ValueError("intentional error")


# ===========================================================================
# Fix 4: File handle leak in export_memories
# ===========================================================================

class TestExportMemoriesFileHandle:
    """export_memories must use a with-statement when opening the export file."""

    def test_export_uses_context_manager_for_file(self, tmp_path):
        """open() in export_memories must be used as a context manager (with statement).

        We verify this indirectly: even if json.dump raises mid-write, the file
        handle is properly closed (no ResourceWarning). We check the source directly.
        """
        import inspect
        import sync

        source = inspect.getsource(sync.export_memories)
        # The with statement means "with open(" appears in the source
        assert "with open(" in source, (
            "export_memories must use `with open(...)` to prevent file handle leaks"
        )

    def test_export_writes_valid_json(self, tmp_path):
        """export_memories actually writes parseable JSON to the output path."""
        import sync

        db_file = str(tmp_path / "mem.db")
        export_file = str(tmp_path / "export.json")

        # We need a real (or mocked) MemoryDB; mock it out
        mock_db = MagicMock()
        mock_db.list_memories.return_value = []
        mock_db.get.return_value = None
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        with patch("sync.MemoryDB", return_value=mock_db):
            sync.export_memories(db_path=db_file, export_path=export_file)

        assert os.path.exists(export_file)
        with open(export_file) as f:
            data = json.load(f)
        assert data == []


# ===========================================================================
# Fix 5: JSON error handling in import_memories
# ===========================================================================

class TestImportMemoriesJsonError:
    """import_memories must handle corrupted/invalid JSON gracefully."""

    def test_corrupted_json_does_not_raise_unhandled(self, tmp_path):
        """Invalid JSON in export file should not propagate JSONDecodeError."""
        import sync

        export_file = tmp_path / "memories-export.json"
        export_file.write_text("{corrupt json[[[")

        db_file = str(tmp_path / "mem.db")
        mock_db = MagicMock()

        with patch("sync.MemoryDB", return_value=mock_db):
            try:
                sync.import_memories(
                    db_path=db_file,
                    export_path=str(export_file),
                )
            except json.JSONDecodeError:
                pytest.fail(
                    "import_memories must catch JSONDecodeError, not propagate it"
                )

    def test_corrupted_json_prints_clear_message(self, tmp_path, capsys):
        """On bad JSON, a human-readable message is printed."""
        import sync

        export_file = tmp_path / "memories-export.json"
        export_file.write_text("not json at all")

        db_file = str(tmp_path / "mem.db")
        mock_db = MagicMock()

        with patch("sync.MemoryDB", return_value=mock_db):
            # May sys.exit(1) — that's acceptable, catch SystemExit
            try:
                sync.import_memories(
                    db_path=db_file,
                    export_path=str(export_file),
                )
            except SystemExit:
                pass

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert output.strip(), "A message must be printed when JSON is corrupted"
        # Should mention something about corruption / re-exporting
        lower = output.lower()
        assert any(word in lower for word in ["corrupt", "invalid", "export", "error"]), (
            f"Message should mention corruption or re-exporting. Got: {output!r}"
        )

    def test_corrupted_json_exits_early_without_db_operations(self, tmp_path):
        """On bad JSON, no DB writes must occur."""
        import sync

        export_file = tmp_path / "memories-export.json"
        export_file.write_text("}}}}}")

        db_file = str(tmp_path / "mem.db")
        mock_db = MagicMock()

        with patch("sync.MemoryDB", return_value=mock_db):
            try:
                sync.import_memories(
                    db_path=db_file,
                    export_path=str(export_file),
                )
            except (SystemExit, json.JSONDecodeError):
                pass

        mock_db.save.assert_not_called()
        mock_db.update.assert_not_called()

    def test_valid_json_still_imports_normally(self, tmp_path):
        """Happy path is unaffected: valid JSON imports without error."""
        import sync

        export_file = tmp_path / "memories-export.json"
        export_file.write_text(json.dumps([
            {
                "id": "abc123",
                "content": "test content",
                "category": "test",
                "updated_at": "2024-01-01T00:00:00",
            }
        ]))

        db_file = str(tmp_path / "mem.db")
        mock_db = MagicMock()
        mock_db.get.return_value = None  # treat as new memory
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        with patch("sync.MemoryDB", return_value=mock_db):
            sync.import_memories(
                db_path=db_file,
                export_path=str(export_file),
            )

        mock_db.save.assert_called_once()


# ===========================================================================
# Fix 6: list_memories sort safety -- replace fragile if-guard with dict maps
# ===========================================================================

class TestListMemoriesSortSafety:
    """list_memories must use explicit dict-lookup maps for sort_by and sort_order.

    The old pattern (if-guard + f-string interpolation) is fragile: a future
    dev could skip the guard and expose a SQL injection surface.  The fix uses
    SORT_MAP / ORDER_MAP so invalid values always fall back to safe defaults,
    regardless of any surrounding guard code.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_db(self):
        """Return a MemoryDB instance with a mock connection (no __init__)."""
        import db as db_module

        mem_db = object.__new__(db_module.MemoryDB)
        mock_conn = MagicMock()
        # Default: execute returns a cursor whose fetchall returns []
        mock_conn.execute.return_value.fetchall.return_value = []
        mem_db.conn = mock_conn
        return mem_db, mock_conn

    def _captured_sql(self, mock_conn) -> str:
        """Return the SQL string passed to the most recent conn.execute call."""
        call_args = mock_conn.execute.call_args
        assert call_args is not None, "conn.execute was never called"
        return call_args[0][0]  # first positional arg (the SQL string)

    # ------------------------------------------------------------------
    # 1. Valid sort_by values must appear verbatim in the query
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("col", ["updated_at", "created_at", "importance", "access_count"])
    def test_valid_sort_by_appears_in_sql(self, col):
        """Each allowed sort_by column name ends up in the ORDER BY clause."""
        mem_db, mock_conn = self._make_db()
        mem_db.list_memories(sort_by=col, sort_order="desc")
        sql = self._captured_sql(mock_conn)
        assert col in sql, (
            f"Expected '{col}' in ORDER BY clause, got: {sql!r}"
        )

    # ------------------------------------------------------------------
    # 2. Invalid sort_by falls back to "updated_at"
    # ------------------------------------------------------------------

    def test_invalid_sort_by_falls_back_to_updated_at(self):
        """An unrecognised sort_by value must produce 'updated_at' in the query."""
        mem_db, mock_conn = self._make_db()
        mem_db.list_memories(sort_by="nonexistent_column", sort_order="desc")
        sql = self._captured_sql(mock_conn)
        assert "updated_at" in sql, (
            f"Invalid sort_by should fall back to 'updated_at'. SQL: {sql!r}"
        )

    # ------------------------------------------------------------------
    # 3. Invalid sort_order falls back to "DESC"
    # ------------------------------------------------------------------

    def test_invalid_sort_order_falls_back_to_desc(self):
        """An unrecognised sort_order value must produce 'DESC' in the query."""
        mem_db, mock_conn = self._make_db()
        mem_db.list_memories(sort_by="updated_at", sort_order="sideways")
        sql = self._captured_sql(mock_conn)
        assert "DESC" in sql.upper(), (
            f"Invalid sort_order should fall back to 'DESC'. SQL: {sql!r}"
        )

    # ------------------------------------------------------------------
    # 4. SQL injection attempt in sort_by is neutralised
    # ------------------------------------------------------------------

    def test_sql_injection_in_sort_by_is_neutralised(self):
        """Injection payload in sort_by must NOT appear in the executed SQL."""
        injection = "updated_at; DROP TABLE memories"
        mem_db, mock_conn = self._make_db()
        mem_db.list_memories(sort_by=injection, sort_order="desc")
        sql = self._captured_sql(mock_conn)
        assert "DROP" not in sql, (
            f"SQL injection payload leaked into query: {sql!r}"
        )
        # Falls back to the safe default instead
        assert "updated_at" in sql, (
            f"Injection sort_by should fall back to 'updated_at'. SQL: {sql!r}"
        )

    # ------------------------------------------------------------------
    # 5. Verify implementation uses dict maps (source inspection)
    # ------------------------------------------------------------------

    def test_implementation_uses_sort_map_dict(self):
        """Source of list_memories must define SORT_MAP as a dict, not an if-guard set."""
        import inspect
        import db as db_module

        source = inspect.getsource(db_module.MemoryDB.list_memories)
        assert "SORT_MAP" in source, (
            "list_memories must use a SORT_MAP dict, not an allowlist set + if-guard"
        )
        assert "ORDER_MAP" in source, (
            "list_memories must use an ORDER_MAP dict, not a bare if-guard"
        )

    def test_implementation_does_not_use_fragile_if_guard(self):
        """Source must NOT use the old `if sort_by not in allowed_sort` pattern."""
        import inspect
        import db as db_module

        source = inspect.getsource(db_module.MemoryDB.list_memories)
        assert "allowed_sort" not in source, (
            "list_memories still uses the old `allowed_sort` set -- replace with SORT_MAP"
        )
