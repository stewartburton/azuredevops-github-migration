# tests/test_verify.py
"""Tests for post-migration verification."""
import pytest
from unittest.mock import Mock, patch
from azuredevops_github_migration.verify import verify_repo_migration


class TestVerifyRepoMigration:
    @patch("azuredevops_github_migration.verify.subprocess.run")
    def test_verify_matching_branches(self, mock_run):
        # Mock git ls-remote for ADO (source)
        ado_output = "abc123\trefs/heads/main\ndef456\trefs/heads/develop\n"
        # Mock git ls-remote for GitHub (target)
        gh_output = "abc123\trefs/heads/main\ndef456\trefs/heads/develop\n"

        mock_run.side_effect = [
            Mock(returncode=0, stdout=ado_output),  # ADO ls-remote
            Mock(returncode=0, stdout=gh_output),    # GitHub ls-remote
        ]

        result = verify_repo_migration(
            ado_url="https://dev.azure.com/org/proj/_git/repo",
            github_url="https://github.com/org/repo.git",
            ado_pat="pat",
            github_token="tok",
        )
        assert result["branch_match"] is True
        assert result["ado_branches"] == 2
        assert result["github_branches"] == 2
        assert result["missing_on_github"] == []

    @patch("azuredevops_github_migration.verify.subprocess.run")
    def test_verify_missing_branch(self, mock_run):
        ado_output = "abc\trefs/heads/main\ndef\trefs/heads/feature\n"
        gh_output = "abc\trefs/heads/main\n"

        mock_run.side_effect = [
            Mock(returncode=0, stdout=ado_output),
            Mock(returncode=0, stdout=gh_output),
        ]

        result = verify_repo_migration(
            ado_url="https://dev.azure.com/org/proj/_git/repo",
            github_url="https://github.com/org/repo.git",
            ado_pat="pat",
            github_token="tok",
        )
        assert result["branch_match"] is False
        assert result["missing_on_github"] == ["feature"]
