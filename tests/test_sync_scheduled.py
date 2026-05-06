"""TDD tests for scheduled_export() and reembed_missing() in sync.py.

Tests the automated export + git commit functionality designed for cron/launchd,
and the post-import re-embedding of memories that lack vector entries.
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Add memory-mcp to path so we can import sync
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "memory-mcp"))

# Mock heavy dependencies before importing sync
sys.modules.setdefault("sqlite_vec", MagicMock())
sys.modules.setdefault("db", MagicMock())
sys.modules.setdefault("hybrid_search", MagicMock())
sys.modules.setdefault("embeddings", MagicMock())

from sync import scheduled_export, export_memories, reembed_missing


@pytest.fixture
def tmp_export(tmp_path):
    """Provide a temporary export file path."""
    return str(tmp_path / "memories-export.json")


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary DB path (doesn't need to exist for mocked tests)."""
    return str(tmp_path / "memory.db")


class TestScheduledExport:
    """Tests for the scheduled_export() function."""

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_calls_export(self, mock_run, mock_export, tmp_export, tmp_db):
        """scheduled_export triggers export_memories."""
        mock_export.return_value = 5
        mock_run.return_value = MagicMock(returncode=1)  # has changes

        scheduled_export(db_path=tmp_db, export_path=tmp_export)

        mock_export.assert_called_once_with(
            db_path=tmp_db, export_path=tmp_export, pretty=True
        )

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_runs_git_add(self, mock_run, mock_export, tmp_export, tmp_db):
        """After export, git add is called on the export file."""
        mock_export.return_value = 5
        mock_run.return_value = MagicMock(returncode=1)  # has changes

        scheduled_export(db_path=tmp_db, export_path=tmp_export)

        # Find the git add call (first subprocess call)
        git_add_call = mock_run.call_args_list[0]
        assert git_add_call[0][0] == ["git", "add", tmp_export]
        assert git_add_call[1]["check"] is True

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_runs_git_commit(self, mock_run, mock_export, tmp_export, tmp_db):
        """After git add, commits with a timestamp message."""
        mock_export.return_value = 5
        # First call (git add) succeeds, second (git diff --cached --quiet) returns 1 (has changes),
        # third (git commit) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff --cached --quiet (1 = has changes)
            MagicMock(returncode=0),  # git commit
        ]

        result = scheduled_export(db_path=tmp_db, export_path=tmp_export)

        commit_call = mock_run.call_args_list[2]
        cmd_args = commit_call[0][0]
        assert cmd_args[0:2] == ["git", "commit"]
        assert any("sync:" in arg for arg in cmd_args)  # message contains "sync:"
        assert result["committed"] is True

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_skips_commit_when_no_changes(self, mock_run, mock_export, tmp_export, tmp_db):
        """If export file is unchanged, skip commit."""
        mock_export.return_value = 5
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git diff --cached --quiet (0 = no changes)
        ]

        result = scheduled_export(db_path=tmp_db, export_path=tmp_export)

        assert result["committed"] is False
        # Should only have 2 subprocess calls (add + diff), no commit
        assert len(mock_run.call_args_list) == 2

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_optionally_pushes(self, mock_run, mock_export, tmp_export, tmp_db):
        """--push flag triggers git push after commit."""
        mock_export.return_value = 5
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
            MagicMock(returncode=0),  # git push
        ]

        result = scheduled_export(db_path=tmp_db, export_path=tmp_export, push=True)

        push_call = mock_run.call_args_list[3]
        assert push_call[0][0] == ["git", "push"]
        assert result["pushed"] is True

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_does_not_push_by_default(self, mock_run, mock_export, tmp_export, tmp_db):
        """Without push=True, no git push is called."""
        mock_export.return_value = 5
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
        ]

        result = scheduled_export(db_path=tmp_db, export_path=tmp_export, push=False)

        assert result["pushed"] is False
        assert len(mock_run.call_args_list) == 3  # add, diff, commit — no push

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_logs_errors_does_not_raise(self, mock_run, mock_export, tmp_export, tmp_db):
        """Git failures are logged, not raised (cron/launchd safety)."""
        mock_export.return_value = 5
        mock_run.side_effect = subprocess.CalledProcessError(1, "git add")

        # Should not raise
        result = scheduled_export(db_path=tmp_db, export_path=tmp_export)

        assert result["error"] is not None

    @patch("sync.export_memories")
    @patch("subprocess.run")
    def test_returns_summary(self, mock_run, mock_export, tmp_export, tmp_db):
        """Returns dict with exported count and git status."""
        mock_export.return_value = 5
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
        ]

        result = scheduled_export(db_path=tmp_db, export_path=tmp_export)

        assert "exported" in result
        assert result["exported"] == 5
        assert "committed" in result
        assert "pushed" in result
        assert "error" in result


class TestReembedMissing:
    """Tests for the reembed_missing() function."""

    def test_embeds_memories_without_vectors(self, tmp_db):
        """Memories with no vector entry get embedded."""
        mock_db = MagicMock()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            (1, "mem_aaa", "how to use pytest fixtures"),
            (2, "mem_bbb", "rate limiting uses sliding window"),
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 768)

        result = asyncio.run(reembed_missing(mock_db, mock_embedder))

        assert result["embedded"] == 2
        assert result["failed"] == 0
        assert mock_embedder.embed.call_count == 2
        assert mock_db.update.call_count == 2

    def test_skips_when_no_missing(self, tmp_db):
        """No work when all memories already have vectors."""
        mock_db = MagicMock()
        mock_db.conn.execute.return_value.fetchall.return_value = []

        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock()

        result = asyncio.run(reembed_missing(mock_db, mock_embedder))

        assert result["embedded"] == 0
        assert result["failed"] == 0
        mock_embedder.embed.assert_not_called()

    def test_counts_failures_when_embedder_returns_none(self, tmp_db):
        """If embedder returns None (service down), count as failed."""
        mock_db = MagicMock()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            (1, "mem_aaa", "some content"),
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=None)

        result = asyncio.run(reembed_missing(mock_db, mock_embedder))

        assert result["embedded"] == 0
        assert result["failed"] == 1
        mock_db.update.assert_not_called()

    def test_queries_only_memories_without_vectors(self, tmp_db):
        """SQL query must use LEFT JOIN ... WHERE IS NULL to find unembedded."""
        mock_db = MagicMock()
        mock_db.conn.execute.return_value.fetchall.return_value = []

        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock()

        asyncio.run(reembed_missing(mock_db, mock_embedder))

        sql_call = mock_db.conn.execute.call_args[0][0]
        assert "LEFT JOIN" in sql_call
        assert "IS NULL" in sql_call


class TestScheduledBackup:
    """Tests for scheduled_backup() — commits memory.db directly to a private repo."""

    @patch("subprocess.run")
    def test_runs_git_add_on_db_file(self, mock_run):
        """git add is called on the DB file."""
        from sync import scheduled_backup
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
        ]

        scheduled_backup(db_path="/tmp/test.db", repo_dir="/tmp/repo")

        git_add = mock_run.call_args_list[0]
        assert git_add[0][0] == ["git", "add", "/tmp/test.db"]
        assert git_add[1]["cwd"] == "/tmp/repo"

    @patch("subprocess.run")
    def test_commits_with_timestamp(self, mock_run):
        """Commits with a sync: prefix and timestamp."""
        from sync import scheduled_backup
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
        ]

        result = scheduled_backup(db_path="/tmp/test.db", repo_dir="/tmp/repo")

        commit_call = mock_run.call_args_list[2]
        cmd_args = commit_call[0][0]
        assert cmd_args[0:2] == ["git", "commit"]
        assert any("sync:" in arg for arg in cmd_args)
        assert result["committed"] is True

    @patch("subprocess.run")
    def test_skips_commit_when_no_changes(self, mock_run):
        """No commit when DB hasn't changed."""
        from sync import scheduled_backup
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git diff --cached --quiet (no changes)
        ]

        result = scheduled_backup(db_path="/tmp/test.db", repo_dir="/tmp/repo")

        assert result["committed"] is False
        assert len(mock_run.call_args_list) == 2

    @patch("subprocess.run")
    def test_never_raises(self, mock_run):
        """Errors are caught, not raised — safe for cron/launchd."""
        from sync import scheduled_backup
        mock_run.side_effect = subprocess.CalledProcessError(128, "git")

        result = scheduled_backup(db_path="/tmp/test.db", repo_dir="/tmp/repo")

        assert result["error"] is not None
        assert result["committed"] is False
