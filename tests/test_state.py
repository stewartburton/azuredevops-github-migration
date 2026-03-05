"""Tests for migration state persistence."""
import json
import os
import threading
import pytest
from azuredevops_github_migration.state import MigrationState


class TestMigrationStateInit:
    def test_creates_new_state_file(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="wave_01")
        assert os.path.exists(state_file)
        assert state.wave == "wave_01"
        assert state.migration_id is not None

    def test_loads_existing_state_file(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        s1 = MigrationState(state_file, wave="wave_01")
        s1.add_repo("ProjectA/repo-1")
        s1.mark_completed("ProjectA/repo-1", github_url="https://github.com/org/repo-1")
        s2 = MigrationState(state_file)
        assert s2.get_status("ProjectA/repo-1") == "completed"
        assert s2.wave == "wave_01"


class TestMigrationStateOperations:
    @pytest.fixture
    def state(self, tmp_path):
        return MigrationState(str(tmp_path / "state.json"), wave="test")

    def test_add_repo(self, state):
        state.add_repo("Proj/repo-a")
        assert state.get_status("Proj/repo-a") == "pending"

    def test_add_repos_bulk(self, state):
        state.add_repos(["Proj/r1", "Proj/r2", "Proj/r3"])
        assert state.get_status("Proj/r1") == "pending"
        assert state.total_repos == 3

    def test_mark_in_progress(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_in_progress("Proj/repo-a", step="cloning")
        assert state.get_status("Proj/repo-a") == "in_progress"

    def test_mark_completed(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_completed("Proj/repo-a", github_url="https://github.com/o/r")
        assert state.get_status("Proj/repo-a") == "completed"

    def test_mark_failed(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_failed("Proj/repo-a", error="timeout")
        assert state.get_status("Proj/repo-a") == "failed"
        info = state.get_repo_info("Proj/repo-a")
        assert info["error"] == "timeout"
        assert info["retry_count"] == 1

    def test_mark_failed_increments_retry(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_failed("Proj/repo-a", error="err1")
        state.mark_failed("Proj/repo-a", error="err2")
        info = state.get_repo_info("Proj/repo-a")
        assert info["retry_count"] == 2

    def test_mark_skipped(self, state):
        state.add_repo("Proj/repo-a")
        state.mark_skipped("Proj/repo-a", reason="empty repo")
        assert state.get_status("Proj/repo-a") == "skipped"


class TestMigrationStateQueries:
    @pytest.fixture
    def state(self, tmp_path):
        s = MigrationState(str(tmp_path / "state.json"), wave="test")
        s.add_repos(["P/r1", "P/r2", "P/r3", "P/r4", "P/r5"])
        s.mark_completed("P/r1", github_url="u1")
        s.mark_completed("P/r2", github_url="u2")
        s.mark_failed("P/r3", error="oops")
        s.mark_in_progress("P/r4", step="cloning")
        return s

    def test_total_repos(self, state):
        assert state.total_repos == 5

    def test_counts(self, state):
        c = state.counts
        assert c["completed"] == 2
        assert c["failed"] == 1
        assert c["in_progress"] == 1
        assert c["pending"] == 1

    def test_pending_repos(self, state):
        assert state.pending_repos == ["P/r5"]

    def test_failed_repos(self, state):
        assert state.failed_repos == ["P/r3"]

    def test_completed_repos(self, state):
        assert set(state.completed_repos) == {"P/r1", "P/r2"}


class TestMigrationStatePersistence:
    def test_survives_reload(self, tmp_path):
        path = str(tmp_path / "state.json")
        s1 = MigrationState(path, wave="w1")
        s1.add_repo("X/y")
        s1.mark_completed("X/y", github_url="url")
        del s1
        s2 = MigrationState(path)
        assert s2.get_status("X/y") == "completed"

    def test_thread_safety(self, tmp_path):
        path = str(tmp_path / "state.json")
        state = MigrationState(path, wave="w1")
        for i in range(20):
            state.add_repo(f"P/r{i}")

        def mark_done(repo_key):
            state.mark_completed(repo_key, github_url=f"url-{repo_key}")

        threads = [threading.Thread(target=mark_done, args=(f"P/r{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert state.counts["completed"] == 20
