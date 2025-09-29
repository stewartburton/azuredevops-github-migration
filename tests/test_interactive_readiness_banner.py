import importlib
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _run(menu_func):
    # Monkeypatch questionary to auto-return 'quit'
    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def ask(self):
            return "quit"

    dummy = types.SimpleNamespace(
        select=lambda *a, **k: DummySelect(), Choice=lambda **k: k
    )
    return dummy


def test_banner_ready(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Ready state: create config & .env and set vars
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / ".env").write_text("")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "abcd1234")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "OrgA")
    monkeypatch.setenv("GITHUB_ORGANIZATION", "GhOrg")
    import azuredevops_github_migration.interactive as inter

    monkeypatch.setattr(inter, "questionary", _run(inter.interactive_menu))
    inter.interactive_menu()
    out = capsys.readouterr().out
    assert "Environment Readiness: READY" in out
    assert "Status:" in out


def test_banner_incomplete(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Only config present, missing env vars
    (tmp_path / "config.json").write_text("{}")
    for k in (
        "AZURE_DEVOPS_PAT",
        "GITHUB_TOKEN",
        "AZURE_DEVOPS_ORGANIZATION",
        "GITHUB_ORGANIZATION",
    ):
        if k in os.environ:
            monkeypatch.delenv(k, raising=False)
    import azuredevops_github_migration.interactive as inter

    monkeypatch.setattr(inter, "questionary", _run(inter.interactive_menu))
    inter.interactive_menu()
    out = capsys.readouterr().out
    assert "Environment Readiness: INCOMPLETE" in out
    assert "Missing:" in out


def test_banner_suppressed(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text("{}")
    monkeypatch.setenv("MIGRATION_NO_BANNER", "1")
    import azuredevops_github_migration.interactive as inter

    monkeypatch.setattr(inter, "questionary", _run(inter.interactive_menu))
    inter.interactive_menu()
    out = capsys.readouterr().out
    assert "Environment Readiness" not in out
