import sys, types, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Dummy analyzer returning multi projects
class DummyClient:
    def get_projects(self):
        return [
            {'name':'Alpha'},
            {'name':'Beta'},
            {'name':'Gamma'},
            {'name':'Delta'},
        ]

class DummyAnalyzer:
    def __init__(self,*a,**k):
        self.client = DummyClient()


def test_interactive_analyze_single_project(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    # minimal config
    (tmp_path / 'config.json').write_text('{}')

    # Patch analyzer
    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)

    # Capture subprocess.run invocations
    calls = []
    def fake_run(cmd,*a,**k):
        calls.append(cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Simulate questionary interactions:
    # 1) analyze scope selection -> choose 'single'
    # 2) project picker -> choose 'Gamma'
    answers = iter([
        'single',   # scope
        'Gamma'     # project selection
    ])
    class FakeSelect:
        def __init__(self, *a, **k):
            pass
        def ask(self):
            try:
                return next(answers)
            except StopIteration:
                return 'quit'
    class FakeQuestionary:
        def select(self, *a, **k):
            return FakeSelect()
        def Choice(self, **k):
            return k.get('value')
    # Provide minimal questionary with select only; _paginated_picker uses text for search but not in this path
    import azuredevops_github_migration.interactive as inter
    monkeypatch.setattr(inter, 'questionary', FakeQuestionary())

    # Force menu iteration: first loop returns 'analyze', second loop 'quit'
    top_answers = iter(['analyze','quit'])
    class TopSelect:
        def __init__(self,*a,**k): pass
        def ask(self): return next(top_answers)
    def top_select(*a,**k): return TopSelect()
    monkeypatch.setattr(inter, 'compute_menu_choices', lambda no_icons: [('analyze','Analyze organization'),('quit','Quit')])
    monkeypatch.setattr(inter.questionary, 'select', top_select)

    inter.interactive_menu()

    # Validate analyze was invoked with --project Gamma
    analyze_cmds = [c for c in calls if 'analyze' in c]
    assert analyze_cmds, 'Expected analyze command invocation'
    found = any('--project' in c and 'Gamma' in c for c in analyze_cmds)
    assert found, f'Expected --project Gamma in analyze commands: {analyze_cmds}'
