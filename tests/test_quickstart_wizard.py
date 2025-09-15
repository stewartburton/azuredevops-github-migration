import sys
from pathlib import Path
import importlib
import types

# Ensure src path importable
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_quickstart(args):
    mod = importlib.import_module('azuredevops_github_migration.quickstart')
    return mod.main(args)


class DummyModule(types.SimpleNamespace):
    def __call__(self, argv=None):  # mimic main([...]) signature if needed
        return 0


def test_quickstart_creates_config_and_runs_doctor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Stub doctor/analyze/init modules by patching their main functions
    def fake_init_main(argv):
        # create minimal config as init would
        (tmp_path / 'config.json').write_text('{}')
        return 0
    def fake_doctor_main(argv):
        return 0
    def fake_analyze_main(argv):
        return 0
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.init', types.SimpleNamespace(main=fake_init_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.doctor', types.SimpleNamespace(main=fake_doctor_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', types.SimpleNamespace(main=fake_analyze_main))
    rc = run_quickstart(['--template','jira-users','--non-interactive'])
    assert rc == 0
    assert (tmp_path / 'config.json').exists()


def test_quickstart_skip_init_and_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Pre-create config
    (tmp_path / 'config.json').write_text('{}')
    calls = {'doctor':0,'analyze':0,'init':0}
    def fake_init_main(argv):
        calls['init'] += 1
        return 0
    def fake_doctor_main(argv):
        calls['doctor'] += 1
        return 0
    def fake_analyze_main(argv):
        calls['analyze'] += 1
        return 0
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.init', types.SimpleNamespace(main=fake_init_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.doctor', types.SimpleNamespace(main=fake_doctor_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', types.SimpleNamespace(main=fake_analyze_main))
    rc = run_quickstart(['--skip-init','--skip-env','--no-analyze','--non-interactive'])
    assert rc == 0
    assert calls['init'] == 0  # skipped
    assert calls['doctor'] == 1
    assert calls['analyze'] == 0


def test_quickstart_handles_doctor_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    def fake_init_main(argv):
        (tmp_path / 'config.json').write_text('{}')
        return 0
    def fake_doctor_main(argv):
        return 1  # failure path but should not abort entire wizard
    def fake_analyze_main(argv):
        return 0
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.init', types.SimpleNamespace(main=fake_init_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.doctor', types.SimpleNamespace(main=fake_doctor_main))
    monkeypatch.setitem(sys.modules, 'azuredevops_github_migration.analyze', types.SimpleNamespace(main=fake_analyze_main))
    rc = run_quickstart(['--non-interactive'])
    assert rc == 0  # still returns 0 (non-blocking doctor issue)