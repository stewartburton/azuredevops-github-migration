import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / 'src'


def test_dotenv_loading(tmp_path, monkeypatch):
    """Ensure that running the CLI loads variables from a .env file in CWD.

    We create a temporary directory with a minimal .env and run the version command.
    Then inside the same process afterward we check that the env var is visible
    ONLY after we purposely import the cli module (which triggers loading). This validates
    that python-dotenv integration works without raising errors.
    """
    # Copy project root cli file path for invocation context

    # Prepare temp working directory with .env
    env_dir = tmp_path
    (env_dir / ".env").write_text("TEST_DOTENV_INJECT=1\n")

    # Run the CLI version command in that directory
    env = os.environ.copy()
    existing = env.get('PYTHONPATH','')
    new_path = str(SRC_PATH)
    if existing:
        if new_path not in existing.split(os.pathsep):
            env['PYTHONPATH'] = new_path + os.pathsep + existing
    else:
        env['PYTHONPATH'] = new_path
    result = subprocess.run(
        [sys.executable, "-m", "azuredevops_github_migration.cli", "--version"],
        cwd=env_dir,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert "Azure DevOps to GitHub Migration Tool" in result.stdout

    # Now import the module in-process with cwd changed to ensure loader sees .env
    monkeypatch.chdir(env_dir)
    if "TEST_DOTENV_INJECT" in os.environ:
        # Should NOT already exist before import if previous subprocess isolation worked
        del os.environ["TEST_DOTENV_INJECT"]

    # Re-import module (force reload) to trigger _load_env_file
    import importlib
    cli_module = importlib.import_module("azuredevops_github_migration.cli")

    # Force call the internal loader (idempotent) and then check
    if hasattr(cli_module, "_load_env_file"):
        cli_module._load_env_file()  # type: ignore

    assert os.environ.get("TEST_DOTENV_INJECT") == "1", \
        "Expected TEST_DOTENV_INJECT to be loaded from .env"
