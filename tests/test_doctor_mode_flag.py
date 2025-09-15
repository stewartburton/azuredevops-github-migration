import json, subprocess, sys, os, re

PACKAGE = 'azuredevops_github_migration'

# We run doctor with different --doctor-mode values and assert expected combined flags effect.
# Using --json for machine-readable validation except for modes that would invoke interactive assist/editor.

MODES_JSON = [
    ('plain', []),
    ('fix', ['fix_env']),
]


def run_doctor(mode):
    cmd = [sys.executable, '-m', PACKAGE + '.doctor', '--doctor-mode', mode, '--json']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_doctor_mode_plain():
    code, out, err = run_doctor('plain')
    assert code in (0,1)  # may fail due to missing env tokens in CI
    data = json.loads(out)
    assert 'tool_version' in data


def test_doctor_mode_fix_adds_field():
    # Remove .env if exists to simulate missing file to allow placeholder append
    if os.path.exists('.env'):
        try: os.remove('.env')
        except Exception: pass
    code, out, err = run_doctor('fix')
    data = json.loads(out)
    # fix_env key should be present with path metadata
    assert 'fix_env' in data
    assert data['fix_env']['path'] == '.env'
