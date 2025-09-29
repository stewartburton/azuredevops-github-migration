import os
from unittest import mock

from azuredevops_github_migration import cli as cli_mod


def test_global_debug_propagates(monkeypatch, capsys):
    # Patch analyze.main to capture args
    captured = {}

    def fake_analyze_main(a):
        captured["args"] = a
        # Simulate success
        return 0

    monkeypatch.setattr(
        "azuredevops_github_migration.analyze.main", fake_analyze_main, raising=False
    )

    cli_mod.main(["--debug", "analyze", "--list-projects"])
    # MIGRATION_DEBUG env var should be set
    assert os.environ.get("MIGRATION_DEBUG") == "1"
    # analyze args should include --debug even though only global was passed
    assert "--debug" in captured.get("args", [])
