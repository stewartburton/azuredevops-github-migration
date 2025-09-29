import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class DummyClient:
    def get_projects(self):
        # Purposely unordered and with different starting letters
        return [
            {"name": "Zeta", "id": "1"},
            {"name": "AlphaProject", "id": "2"},
            {"name": "BetaSample", "id": "3"},
            {"name": "GammaTool", "id": "4"},
            {"name": "DeltaService", "id": "5"},
        ]


class DummyAnalyzer:
    def __init__(self, *a, **k):
        self.client = DummyClient()


def test_quickstart_search_filter(monkeypatch, capsys):
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(
        sys.modules, "azuredevops_github_migration.analyze", fake_analyze
    )
    import azuredevops_github_migration.quickstart as qs

    # Sequence of answers:
    # 1) Open selection page -> choose 'Search / filter'
    # 2) Provide search term 'gs' (matches 'GammaTool' via fuzzy g..s?) Actually choose 'gt' to fuzzy match 'GammaTool'
    # 3) Select 'GammaTool'

    answers = iter(
        [
            "Search / filter",  # first menu choose search
            "GammaTool",  # final selection after filtering
        ]
    )

    class FakeQuestionary:
        def select(self, *a, **k):
            next_answer = next(answers)

            class Resp:
                def ask(self_inner):
                    return next_answer

            return Resp()

        def text(self, prompt):
            class T:
                def ask(self_inner):
                    return "gt"

            return T()

    monkeypatch.setattr(qs, "questionary", FakeQuestionary())

    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    rc = qs.main(["--skip-env", "--skip-init"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "GammaTool" in out
    assert "Analyze selected project" in out


def test_quickstart_jump_to_letter(monkeypatch, capsys):
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(
        sys.modules, "azuredevops_github_migration.analyze", fake_analyze
    )
    import azuredevops_github_migration.quickstart as qs

    # Simulate jump to letter 'D' and then select DeltaService
    answers = iter(
        [
            "Jump to letter",  # first selection triggers letter prompt
            "DeltaService",  # final selection
        ]
    )

    class FakeQuestionary:
        def select(self, *a, **k):
            next_answer = next(answers)

            class Resp:
                def ask(self_inner):
                    return next_answer

            return Resp()

        def text(self, prompt):
            class T:
                def ask(self_inner):
                    return "D"

            return T()

    monkeypatch.setattr(qs, "questionary", FakeQuestionary())

    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    rc = qs.main(["--skip-env", "--skip-init"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DeltaService" in out
    assert "Analyze selected project" in out
