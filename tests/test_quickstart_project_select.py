import sys
from pathlib import Path
import importlib
import types

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_quickstart(args):
    mod = importlib.import_module('azuredevops_github_migration.quickstart')
    return mod.main(args)

class DummyClient:
    def get_projects(self):
        return [
            {'name':'Alpha','id':'1','visibility':'private'},
            {'name':'Beta Project','id':'2','visibility':'private'}
        ]

class DummyAnalyzer:
    def __init__(self, *a, **k):
        self.client = DummyClient()


def test_project_selection(monkeypatch, capsys):
    # Inject fake analyze module with AzureDevOpsAnalyzer
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    # Provide questionary mock that returns second project
    class DummyQ:
        def select(self, *a, **k):
            # Simulate single page; just return second project
            class X:
                def ask(self_inner):
                    return 'Beta Project'
            return X()
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    # Avoid interactive menu prompt waiting for stdin
    monkeypatch.setattr('builtins.input', lambda *a, **k: 'n')
    rc = run_quickstart(['--skip-env','--skip-init'])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Project 'Beta Project' selected" in out
    assert 'migrate --project "Beta Project"' in out


def test_project_selection_analyze_recommendation(monkeypatch, capsys):
    """Ensure analyze recommendation uses --project when a project is selected."""
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    class DummyQ:
        def select(self, *a, **k):
            class X:
                def ask(self_inner):
                    return 'Beta Project'
            return X()
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    # Simulate declining interactive menu prompt
    monkeypatch.setattr('builtins.input', lambda *a, **k: 'n')
    rc = run_quickstart(['--skip-env','--skip-init'])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'analyze --project "Beta Project" --create-plan' in out
    assert '(Full org analysis:' in out


def test_open_menu_flag(monkeypatch, capsys):
    """--open-menu should call interactive_menu without prompting."""
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    # Bypass project selection for speed
    class DummyQ:
        def select(self, *a, **k):
            class X:
                def ask(self_inner):
                    return 'Alpha'
            return X()
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    # Stub interactive_menu
    called = {}
    def fake_menu():
        called['yes'] = True
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.interactive', types.SimpleNamespace(interactive_menu=fake_menu))
    rc = run_quickstart(['--skip-env','--skip-init','--open-menu'])
    assert rc == 0
    assert called.get('yes') is True


def test_open_menu_prompt_yes(monkeypatch, capsys):
    """Prompt path (no --open-menu) with user accepting should invoke menu."""
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    class DummyQ:
        def select(self, *a, **k):
            class X:
                def ask(self_inner):
                    return 'Alpha'
            return X()
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    called = {}
    def fake_menu():
        called['prompt'] = True
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.interactive', types.SimpleNamespace(interactive_menu=fake_menu))
    monkeypatch.setattr('builtins.input', lambda *a, **k: '')  # accept default (yes)
    rc = run_quickstart(['--skip-env','--skip-init'])
    assert rc == 0
    assert called.get('prompt') is True


def test_open_menu_prompt_no(monkeypatch, capsys):
    """Prompt path with explicit 'n' should not invoke menu."""
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    class DummyQ:
        def select(self, *a, **k):
            class X:
                def ask(self_inner):
                    return 'Alpha'
            return X()
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    called = {}
    def fake_menu():
        called['prompt'] = True
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.interactive', types.SimpleNamespace(interactive_menu=fake_menu))
    monkeypatch.setattr('builtins.input', lambda *a, **k: 'n')
    rc = run_quickstart(['--skip-env','--skip-init'])
    assert rc == 0
    assert called.get('prompt') is not True


def test_project_selection_disabled(monkeypatch, capsys):
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)
    import azuredevops_github_migration.quickstart as qs
    class DummyQ:
        def select(self, *a, **k):
            raise AssertionError('select should not be called when disabled')
    monkeypatch.setattr(qs, 'questionary', DummyQ())
    monkeypatch.setattr('builtins.input', lambda *a, **k: 'n')
    rc = run_quickstart(['--skip-env','--skip-init','--no-project-select'])
    assert rc == 0
    out = capsys.readouterr().out
    assert '<Project>' in out
    assert 'selected for examples' not in out
