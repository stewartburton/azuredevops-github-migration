import json
import os
import subprocess
import sys
from pathlib import Path


def _run_doctor(args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "azuredevops_github_migration.doctor", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )


def test_doctor_json_env_includes_masked_values(tmp_path, monkeypatch):
    env_dir = tmp_path
    (env_dir / ".env").write_text("AZURE_DEVOPS_PAT=abcd1234\nGITHUB_TOKEN=ghp_secretvalue\nLOG_LEVEL=DEBUG\n")
    proc = _run_doctor(["--json"], env_dir)
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert "environment" in data
    env_section = data["environment"]
    assert env_section["AZURE_DEVOPS_PAT"]["present"] is True
    # Masked value should not expose full secret
    masked = env_section["AZURE_DEVOPS_PAT"].get("value_masked", "")
    assert masked.startswith("abcd") and "1234" not in masked[4:], "Masking failed to obfuscate remainder"


def test_doctor_print_env_shows_masked(tmp_path):
    env_dir = tmp_path
    (env_dir / ".env").write_text("GITHUB_TOKEN=ghp_ABCDEFG\n")
    proc = _run_doctor(["--print-env"], env_dir)
    assert proc.returncode in (0, 1)
    combined = proc.stdout + "\n" + proc.stderr
    # Ensure some output was produced
    assert "GITHUB_TOKEN" in combined
    assert "SET" in combined
    # Mask should not reveal full secret tail
    assert "ABCDEFG" not in combined, "Unmasked secret leaked"
