import json
import builtins
from unittest import mock

from azuredevops_github_migration import analyze as analyze_mod


class DummyClient:
    def __init__(self):
        pass
    def get_projects(self):
        return [
            {'name': 'ProjA', 'id': '1', 'visibility': 'private'},
            {'name': 'ProjB', 'id': '2', 'visibility': 'public'}
        ]
    def get_repositories(self, project):
        if project == 'ProjA':
            return [{'name': 'Repo1', 'id': 'r1'}, {'name': 'Repo2', 'id': 'r2'}]
        return []


def minimal_config(tmp_path):
    cfg = {
        "azure_devops": {"organization": "org", "personal_access_token": "PAT123456"}
    }
    p = tmp_path / 'config.json'
    p.write_text(json.dumps(cfg))
    return str(p)


def run_main(args, monkeypatch):
    # Patch AzureDevOpsAnalyzer to inject dummy client after init
    real_init = analyze_mod.AzureDevOpsAnalyzer.__init__
    def _init(self, config_file, skip_work_items=False, omit_work_item_fields=False):
        real_init(self, config_file, skip_work_items, omit_work_item_fields)
        self.client = DummyClient()
    monkeypatch.setattr(analyze_mod.AzureDevOpsAnalyzer, '__init__', _init)
    return analyze_mod.main(args)


def test_list_projects_flag(monkeypatch, tmp_path, capsys):
    cfg = minimal_config(tmp_path)
    code = run_main(['--config', cfg, '--list-projects'], monkeypatch)
    captured = capsys.readouterr().out
    assert code == 0
    assert 'ProjA' in captured and 'ProjB' in captured


def test_list_repos_flag(monkeypatch, tmp_path, capsys):
    cfg = minimal_config(tmp_path)
    code = run_main(['--config', cfg, '--list-repos', 'ProjA'], monkeypatch)
    captured = capsys.readouterr().out
    assert code == 0
    assert 'Repo1' in captured and 'Repo2' in captured


def test_debug_echo(monkeypatch, tmp_path, capsys):
    cfg = minimal_config(tmp_path)
    code = run_main(['--config', cfg, '--list-projects', '--debug'], monkeypatch)
    captured = capsys.readouterr().out
    assert code == 0
    # Should contain sanitized PAT (ends with last 4) and not full token
    assert '***3456' in captured
    assert 'PAT123456"' not in captured  # full token should not appear