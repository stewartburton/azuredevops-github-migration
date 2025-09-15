import sys, types, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

class DummyClient:
    def get_projects(self):
        return [ {'name':'Alpha'}, {'name':'Beta'} ]
    def get_repositories(self, project):
        if project == 'Alpha':
            return [{'name':'RepoOne'},{'name':'RepoTwo'}]
        return []

class DummyAnalyzer:
    def __init__(self,*a,**k):
        self.client = DummyClient()


def test_interactive_migrate_dry_run(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.json').write_text('{}')

    fake_analyze = types.SimpleNamespace(AzureDevOpsAnalyzer=DummyAnalyzer)
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', fake_analyze)

    calls = []
    def fake_run(cmd,*a,**k):
        calls.append(cmd)
        class R: returncode = 0
        return R()
    monkeypatch.setattr(subprocess, 'run', fake_run)

    # Answer sequence for migrate path:
    # top-level: 'migrate', then 'quit' to exit loop afterwards
    # project picker: choose 'Alpha'
    # repo picker: choose 'RepoTwo'
    # mode: choose 'dry'
    # custom github repo name: blank
    answers = iter(['migrate','quit'])

    import azuredevops_github_migration.interactive as inter

    # Provide picker answers by overriding _paginated_picker
    monkeypatch.setattr(inter, '_paginated_picker', lambda *a, **k: 'Alpha' if 'project' in a[0].lower() else 'RepoTwo')

    # Fake questionary for mode select & text
    class FakeSelect:
        def __init__(self,*a,**k): pass
        def ask(self): return 'dry'
    class FakeText:
        def ask(self): return ''
    class FakeQ:
        def select(self,*a,**k): return FakeSelect()
        def text(self,*a,**k): return FakeText()
        def Choice(self, **k): return k.get('value')
    monkeypatch.setattr(inter, 'questionary', FakeQ())

    class TopSelect:
        def __init__(self,*a,**k): pass
        def ask(self): return next(answers)
    monkeypatch.setattr(inter.questionary, 'select', lambda *a, **k: TopSelect())
    monkeypatch.setattr(inter, 'compute_menu_choices', lambda no_icons: [('migrate','Migrate repository'),('quit','Quit')])

    inter.interactive_menu()

    migrate_cmds = [c for c in calls if 'migrate' in c and '--project' in c]
    assert migrate_cmds, 'Expected migrate command invocation'
    cmd = migrate_cmds[0]
    assert '--dry-run' in cmd, 'Dry run flag missing'
    assert 'Alpha' in cmd and 'RepoTwo' in cmd
