"""
Interactive CLI enhancements for Azure DevOps to GitHub Migration Tool
"""
import subprocess
import sys
import os
import shutil
from typing import List

try:  # Optional dependency
    import questionary  # type: ignore
except Exception:  # pragma: no cover - optional
    questionary = None


def _find_powershell() -> List[str]:
    """Return a command list to invoke PowerShell Core (pwsh) or Windows PowerShell fallback.

    We prefer pwsh for cross-platform consistency. Returns an empty list if neither is found.
    """
    candidates = [
        os.environ.get("PWSH_PATH"),  # explicit override
        "pwsh",
        "powershell",
        "powershell.exe",
    ]
    for c in candidates:
        if not c:
            continue
        path = shutil.which(c) if not os.path.isabs(c) else (c if os.path.exists(c) else None)
        if path:
            # Use -NoProfile for predictable behavior
            if os.path.basename(path).lower().startswith("pwsh"):
                return [path, "-NoLogo", "-NoProfile", "-File"]
            return [path, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    return []


def run_update_env(path: str = '.env') -> int:
    """Run Test-MigrationEnv.ps1 to load/update environment variables into current session.

    The PowerShell script only affects the spawned process; we mimic update by reading the
    .env after script execution (the script does not modify file contents—its purpose is
    loading). If .env missing we create a stub template.
    """
    script_relative = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'Test-MigrationEnv.ps1')
    script_path = os.path.abspath(script_relative)
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}")
        return 1

    # Ensure a stub .env exists so script doesn't fail prematurely
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write('# Auto-created .env stub -- fill in values or re-run update-env\n')
            f.write('AZURE_DEVOPS_PAT=\nGITHUB_TOKEN=\nAZURE_DEVOPS_ORGANIZATION=\nGITHUB_ORGANIZATION=\n')
        print(f"Created stub {path}. Populate credential values or re-run to load.")

    shell_cmd = _find_powershell()
    if not shell_cmd:
        print("No PowerShell host available (pwsh / powershell). Install PowerShell 7+ for this feature.")
        return 1

    cmd = shell_cmd + [script_path, '-Load', '-Overwrite', '-Path', path, '-Json']
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:  # pragma: no cover
        print(f"Failed to execute PowerShell script: {e}")
        return 1

    if proc.returncode != 0:
        print("Environment load script exited with errors:")
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        return proc.returncode

    print("Environment variables processed. Summary (masked):")
    print(proc.stdout.strip())
    # Load .env into current Python process for immediate use by user commands
    _simple_env_load(path)
    return 0


def _simple_env_load(path: str):
    try:
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:  # pragma: no cover
        print(f"[WARN] Could not load env file into current process: {e}")


def interactive_menu():
    """Show interactive CLI menu with keyboard navigation (questionary)."""
    if not questionary:
        print("Optional dependency 'questionary' not installed. Install with: pip install questionary")
        return 1
    choices = [
        "Init configuration files",
        "Migrate repository",
        "Analyze organization",
        "Batch migrate",
        "Doctor diagnostics",
        "Update / load .env",
        "Quit"
    ]
    while True:
        selection = questionary.select("Choose an action:", choices=choices).ask()
        if selection is None:  # user aborted (Ctrl+C)
            print("Aborted.")
            return 1
        key = selection.lower().split()[0]
        if key == 'init':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'init'])
        elif key == 'migrate':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'migrate'])
        elif key == 'analyze':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'analyze'])
        elif key == 'batch':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'batch'])
        elif key == 'doctor':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor'])
        elif key == 'update':
            run_update_env()
        elif key == 'quit':
            print("Exiting interactive menu.")
            break
    return 0
