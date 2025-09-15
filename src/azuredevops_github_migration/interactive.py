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
            f.write('# Auto-created .env stub -- fill in values. Never commit real secrets.\n')
            f.write('# Required tokens\n')
            f.write('AZURE_DEVOPS_PAT=\n')
            f.write('GITHUB_TOKEN=\n')
            f.write('\n# Organization slugs (aliases: AZURE_DEVOPS_ORG / GITHUB_ORG)\n')
            f.write('AZURE_DEVOPS_ORGANIZATION=\n')
            f.write('GITHUB_ORGANIZATION=\n')
            f.write('\n# Optional custom endpoints (usually leave default)\n')
            f.write('# AZURE_DEVOPS_BASE_URL=https://dev.azure.com\n')
            f.write('# GITHUB_BASE_URL=https://api.github.com\n')
        print(f"Created stub {path}. Populate credential and organization values, then re-run update-env.")

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
    # Logical ordering: prepare & validate first, then analysis, planning, migration, support
    # 1. Update env, 2. Doctor, 3. Init, 4. Analyze, 5. Batch, 6. Migrate, 7. Quit
    color_disabled = bool(os.environ.get('NO_COLOR'))
    no_icons = bool(os.environ.get('MIGRATION_CLI_NO_ICONS'))

    # ANSI color support (questionary does not parse custom [color] tags in titles)
    # Colors disabled inside menu because questionary does not reliably render ANSI in choices across all environments.
    # We retain a legend (printed once) if colors are not disabled, purely informational.
    def style(txt: str, _color: str) -> str:  # stylistic no-op now
        return txt

    ico = (lambda sym: sym if (not no_icons) else '')

    # Using explicit Choice objects allows future metadata
    choices = [
        questionary.Choice(title=f"{ico('🔐 ')}Update / load .env", value='update'),
        # Single doctor entry opens a submenu of diagnostic modes
        questionary.Choice(title=f"{ico('🩺 ')}Doctor diagnostics", value='doctor_menu'),
        questionary.Choice(title=f"{ico('🛠  ')}Init configuration files", value='init'),
        questionary.Choice(title=f"{ico('🔎 ')}Analyze organization", value='analyze'),
        questionary.Choice(title=f"{ico('📦 ')}Batch migrate", value='batch'),
        questionary.Choice(title=f"{ico('🚚 ')}Migrate repository", value='migrate'),
        questionary.Choice(title=f"{ico('❌ ')}Quit", value='quit'),
    ]

    help_footer = (
        "Use arrow keys • Enter to run • ESC/Ctrl+C to abort | Set NO_COLOR=1 to disable colors, "
        "MIGRATION_CLI_NO_ICONS=1 to hide emojis"
    )

    if not color_disabled:
        print("(Interactive Menu) — Icons indicate action category. Set MIGRATION_CLI_NO_ICONS=1 to disable icons.")

    while True:
        selection = questionary.select(
            "Choose an action:", choices=choices, instruction="",
            qmark="➡" if not no_icons else "?",
        ).ask()
        if selection is None:  # user aborted (Ctrl+C)
            print("Aborted.")
            return 1
        key = selection  # value already mapped
        if key == 'init':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'init'])
        elif key == 'migrate':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'migrate'])
        elif key == 'analyze':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'analyze'])
        elif key == 'batch':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'batch'])
        elif key == 'doctor_menu':
            # Submenu for doctor operations (replaces previous separate entries)
            sub = questionary.select(
                "Doctor diagnostics:",
                choices=[
                    questionary.Choice(title="Run diagnostics", value='plain'),
                    questionary.Choice(title="Diagnostics + append placeholders (--fix-env)", value='fix'),
                    questionary.Choice(title="Diagnostics + interactive remediation (--assist)", value='assist'),
                    questionary.Choice(title="Diagnostics + fix + remediation (--fix-env --assist)", value='fix_assist'),
                    questionary.Choice(title="Edit & save .env (--edit-env)", value='edit_env'),
                    questionary.Choice(title="Edit .env then remediation (--edit-env --assist)", value='edit_env_assist'),
                    questionary.Choice(title="Back", value='back'),
                ],
                qmark='🩺' if not no_icons else '?'
            ).ask()
            if sub == 'plain':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor'])
            elif sub == 'fix':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--fix-env'])
            elif sub == 'assist':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--assist'])
            elif sub == 'fix_assist':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--fix-env', '--assist'])
            elif sub == 'edit_env':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--edit-env'])
            elif sub == 'edit_env_assist':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--edit-env', '--assist'])
            else:  # back or None
                continue
        elif key == 'update':
            run_update_env()
        elif key == 'quit':
            print("Exiting interactive menu.")
            break
    return 0
