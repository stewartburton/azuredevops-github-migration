"""Tests for parallel batch migration with state tracking."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from azuredevops_github_migration.batch_migrate import (
    load_migration_plan,
    run_batch_migration,
)
from azuredevops_github_migration.state import MigrationState


class TestLoadMigrationPlan:
    def test_load_valid_plan(self, tmp_path):
        plan_file = tmp_path / "plan.json"
        plan_data = [
            {"project_name": "P1", "repo_name": "r1", "github_repo_name": "r1"},
            {"project_name": "P1", "repo_name": "r2"},
        ]
        plan_file.write_text(json.dumps(plan_data))
        result = load_migration_plan(str(plan_file))
        assert len(result) == 2
        assert result[0]["project_name"] == "P1"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_migration_plan("/nonexistent.json")


class TestRunBatchMigration:
    @patch("azuredevops_github_migration.batch_migrate.MigrationOrchestrator")
    def test_skips_completed_repos(self, MockOrch, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="test")
        state.add_repo("P1/r1")
        state.mark_completed("P1/r1", github_url="u")
        state.add_repo("P1/r2")

        plan = [
            {"project_name": "P1", "repo_name": "r1"},
            {"project_name": "P1", "repo_name": "r2"},
        ]

        mock_orch = Mock()
        mock_orch.migrate_repository.return_value = True
        MockOrch.return_value = mock_orch

        results = run_batch_migration(
            plan, config_file="dummy.json", state=state, concurrency=1, dry_run=True
        )
        # r1 already completed, so only r2 should be attempted
        assert mock_orch.migrate_repository.call_count == 1

    @patch("azuredevops_github_migration.batch_migrate.MigrationOrchestrator")
    def test_retry_failed_only(self, MockOrch, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = MigrationState(state_file, wave="test")
        state.add_repos(["P/r1", "P/r2", "P/r3"])
        state.mark_completed("P/r1", github_url="u")
        state.mark_failed("P/r2", error="oops")
        # r3 pending

        plan = [
            {"project_name": "P", "repo_name": "r1"},
            {"project_name": "P", "repo_name": "r2"},
            {"project_name": "P", "repo_name": "r3"},
        ]

        mock_orch = Mock()
        mock_orch.migrate_repository.return_value = True
        MockOrch.return_value = mock_orch

        results = run_batch_migration(
            plan, config_file="dummy.json", state=state, concurrency=1,
            dry_run=True, retry_failed=True
        )
        # retry_failed=True: only r2 (failed) should be retried
        assert mock_orch.migrate_repository.call_count == 1
