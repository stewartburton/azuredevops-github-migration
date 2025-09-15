import os
import importlib
import sys
from pathlib import Path

# Ensure src path importable without editable install
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_module():
    return importlib.import_module('azuredevops_github_migration.interactive')


def extract_values(pairs):
    return [v for v, _ in pairs]


def test_menu_without_files_includes_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = load_module()
    choices = mod.compute_menu_choices(no_icons=True)
    vals = extract_values(choices)
    assert 'doctor_menu' in vals
    assert 'init' in vals  # should appear when files missing
    assert 'quit' in vals
    # update-env should not be top-level anymore
    assert 'update' not in vals and 'update_env' not in vals


def test_menu_with_existing_files_omits_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # create config.json and .env
    (tmp_path / 'config.json').write_text('{}')
    (tmp_path / '.env').write_text('AZURE_DEVOPS_PAT=foo\nGITHUB_TOKEN=bar')
    mod = load_module()
    choices = mod.compute_menu_choices(no_icons=False)
    vals = extract_values(choices)
    assert 'doctor_menu' in vals
    assert 'init' not in vals  # hidden when both present
    assert 'migrate' in vals
    assert 'quit' in vals


def test_menu_force_show_init(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.json').write_text('{}')
    (tmp_path / '.env').write_text('')
    # already would show because .env empty, now create .env and config then force
    (tmp_path / '.env').write_text('AZURE_DEVOPS_PAT=foo')
    os.environ['MIGRATION_SHOW_INIT_ALWAYS'] = '1'
    try:
        mod = load_module()
        choices = mod.compute_menu_choices(no_icons=True)
        vals = extract_values(choices)
        assert 'init' in vals
    finally:
        os.environ.pop('MIGRATION_SHOW_INIT_ALWAYS', None)
