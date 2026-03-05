# tests/test_status.py
"""Tests for CLI status dashboard."""
import pytest
from azuredevops_github_migration.state import MigrationState
from azuredevops_github_migration.status import format_status_report


class TestFormatStatusReport:
    @pytest.fixture
    def state(self, tmp_path):
        s = MigrationState(str(tmp_path / "s.json"), wave="w1")
        s.add_repos(["P/r1", "P/r2", "P/r3", "P/r4", "P/r5"])
        s.mark_completed("P/r1", github_url="u1")
        s.mark_completed("P/r2", github_url="u2")
        s.mark_failed("P/r3", error="timeout")
        s.mark_in_progress("P/r4", step="cloning")
        return s

    def test_report_contains_counts(self, state):
        report = format_status_report(state)
        assert "Completed:" in report
        assert "Failed:" in report
        assert "Pending:" in report
        assert "In Progress:" in report

    def test_report_contains_wave(self, state):
        report = format_status_report(state)
        assert "w1" in report

    def test_report_shows_errors(self, state):
        report = format_status_report(state, show_errors=True)
        assert "timeout" in report

    def test_empty_state(self, tmp_path):
        s = MigrationState(str(tmp_path / "s.json"), wave="empty")
        report = format_status_report(s)
        assert "0" in report
