import importlib
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_quickstart(args):
    mod = importlib.import_module("azuredevops_github_migration.quickstart")
    return mod.main(args)


def test_quickstart_autopatch_placeholders(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Create placeholder config resembling older template
    config = {
        "azure_devops": {
            "organization": "your-organization-name",
            "personal_access_token": "${AZURE_DEVOPS_PAT}",
        },
        "github": {"organization": "your-github-org", "token": "${GITHUB_TOKEN}"},
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    # Set environment variables that should be injected
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "RealAzOrg")
    monkeypatch.setenv("GITHUB_ORGANIZATION", "RealGhOrg")

    # Stub doctor/analyze to avoid external logic
    def fake_doctor_main(argv):
        return 0

    def fake_analyze_main(argv):
        return 0

    monkeypatch.setitem(
        sys.modules,
        "azuredevops_github_migration.doctor",
        types.SimpleNamespace(main=fake_doctor_main),
    )
    monkeypatch.setitem(
        sys.modules,
        "azuredevops_github_migration.analyze",
        types.SimpleNamespace(main=fake_analyze_main),
    )

    rc = run_quickstart(["--skip-env", "--no-analyze", "--non-interactive"])
    assert rc == 0
    new_cfg = json.loads((tmp_path / "config.json").read_text())
    assert new_cfg["azure_devops"]["organization"] == "RealAzOrg"
    assert new_cfg["github"]["organization"] == "RealGhOrg"
    # Backup file created
    backups = list(tmp_path.glob("config.json.bak.*"))
    assert backups, "Backup file not created"
