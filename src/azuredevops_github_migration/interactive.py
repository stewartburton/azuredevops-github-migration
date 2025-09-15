"""
Interactive CLI enhancements for Azure DevOps to GitHub Migration Tool
"""
import subprocess
import sys
import os
import shutil
from typing import List, Sequence, Dict, Optional, Callable

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
            f.write('\n# Organization names (aliases: AZURE_DEVOPS_ORG / GITHUB_ORG)\n')
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


def compute_menu_choices(no_icons: bool) -> Sequence[tuple[str, str]]:
    """Return sequence of (value, title_without_qmark) for top-level menu (testable).

    Excludes the env update action as a top-level item (now nested under doctor submenu).
    """
    ico = (lambda sym: sym if (not no_icons) else '')
    items: list[tuple[str, str]] = []
    # Doctor always present (environment actions nested within)
    items.append(('doctor_menu', f"{ico('🩺 ')}Doctor diagnostics"))
    # Conditionally include init
    config_missing = not os.path.exists('config.json')
    env_missing = not os.path.exists('.env')
    show_init_always = bool(os.environ.get('MIGRATION_SHOW_INIT_ALWAYS'))
    if config_missing or env_missing or show_init_always:
        items.append(('init', f"{ico('🛠  ')}Init configuration files"))
    # Core flow actions
    items.extend([
        ('analyze', f"{ico('🔎 ')}Analyze organization"),
        ('batch', f"{ico('📦 ')}Batch migrate"),
        ('migrate', f"{ico('🚚 ')}Migrate repository"),
        ('quit', f"{ico('❌ ')}Quit"),
    ])
    return items


PLACEHOLDER_PREFIXES = (
    'your_azure_devops_personal_access_token',
    'your_github_personal_access_token',
    'your_azure_devops_org',
    'your_github_org'
)

def _mask(val: str | None) -> str:
    if not val:
        return ''
    if len(val) <= 4:
        return val[0] + '***' if len(val) > 1 else '****'
    return val[:4] + '****'

def _gather_readiness() -> Dict[str, any]:
    cfg_exists = os.path.exists('config.json')
    env_exists = os.path.exists('.env')
    # Core vars
    core = ['AZURE_DEVOPS_PAT','GITHUB_TOKEN','AZURE_DEVOPS_ORGANIZATION','GITHUB_ORGANIZATION']
    status = {}
    all_present = True
    any_placeholders = False
    for k in core:
        raw = os.environ.get(k)
        present = bool(raw)
        placeholder = False
        if present:
            low = raw.lower()
            for p in PLACEHOLDER_PREFIXES:
                if low.startswith(p):
                    placeholder = True
                    any_placeholders = True
                    break
        else:
            all_present = False
        status[k] = {
            'present': present,
            'placeholder': placeholder,
            'masked': _mask(raw)
        }
    readiness_level = 'READY' if (cfg_exists and env_exists and all_present and not any_placeholders) else 'INCOMPLETE'
    return {
        'config': cfg_exists,
        'env_file': env_exists,
        'all_present': all_present,
        'any_placeholders': any_placeholders,
        'vars': status,
        'level': readiness_level
    }

def _print_readiness_banner():
    if os.environ.get('MIGRATION_NO_BANNER') == '1':
        return
    r = _gather_readiness()
    level = r['level']
    # Simple color codes (can be disabled by NO_COLOR from earlier logic)
    green = '\033[92m'
    yellow = '\033[93m'
    reset = '\033[0m'
    color_disabled = bool(os.environ.get('NO_COLOR'))
    if color_disabled:
        green = yellow = reset = ''
    if level == 'READY':
        print(f"{green}=== Environment Readiness: READY ==={reset}")
        print("Config + .env detected; all core variables set (no placeholders).")
    else:
        print(f"{yellow}=== Environment Readiness: INCOMPLETE ==={reset}")
        missing = [k for k,v in r['vars'].items() if not v['present']]
        placeholders = [k for k,v in r['vars'].items() if v['placeholder']]
        if not r['config']:
            print(" - config.json missing (run init)")
        if not r['env_file']:
            print(" - .env missing (run doctor --edit-env or init)")
        if missing:
            print(" - Missing: " + ", ".join(missing))
        if placeholders:
            print(" - Placeholders: " + ", ".join(placeholders) + " (edit via doctor --edit-env)")
        print("Use Doctor submenu → 'Enter / update environment variables' to fix.")
    # Compact variable summary line
    compact = []
    for k in ('AZURE_DEVOPS_PAT','GITHUB_TOKEN','AZURE_DEVOPS_ORGANIZATION','GITHUB_ORGANIZATION'):
        v = r['vars'][k]
        state = 'OK' if v['present'] and not v['placeholder'] else ('PH' if v['placeholder'] else 'MISSING')
        compact.append(f"{k.split('_')[-1]}={state}")
    print("Status: " + ' '.join(compact))


def interactive_menu():
    """Show interactive CLI menu with keyboard navigation (questionary)."""
    if not questionary:
        print("Optional dependency 'questionary' not installed. Install with: pip install questionary")
        return 1
    color_disabled = bool(os.environ.get('NO_COLOR'))
    no_icons = bool(os.environ.get('MIGRATION_CLI_NO_ICONS'))
    if not color_disabled:
        print("(Interactive Menu) — Icons indicate action category. Set MIGRATION_CLI_NO_ICONS=1 to disable icons.")
    _print_readiness_banner()

    # Build menu choices (value, title) then convert to questionary Choice objects
    top_level = compute_menu_choices(no_icons)
    q_choices = [questionary.Choice(title=title, value=val) for val, title in top_level]

    while True:
        selection = questionary.select(
            "Choose an action:", choices=q_choices, instruction="",
            qmark="➡" if not no_icons else "?",
        ).ask()
        if selection is None:
            print("Aborted.")
            return 1
        key = selection
        if key == 'init':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'init'])
        elif key == 'migrate':
            # Interactive migrate wizard
            try:
                from .analyze import AzureDevOpsAnalyzer
                analyzer = AzureDevOpsAnalyzer('config.json', skip_work_items=True, omit_work_item_fields=True)
                projects = analyzer.client.get_projects()
                project_names = sorted([p['name'] for p in projects], key=lambda s: s.lower())
                if not project_names:
                    print("No projects available to migrate from.")
                    continue
                if len(project_names) == 1:
                    project = project_names[0]
                else:
                    project = _paginated_picker("Select source project", project_names, allow_cancel=True)
                if not project:
                    continue
                # Fetch repositories for selected project
                repos = analyzer.client.get_repositories(project)
                repo_names = sorted([r['name'] for r in repos], key=lambda s: s.lower())
                if not repo_names:
                    print(f"Project '{project}' has no repositories.")
                    continue
                if len(repo_names) == 1:
                    repo = repo_names[0]
                else:
                    repo = _paginated_picker(f"Select repository in {project}", repo_names, allow_cancel=True)
                if not repo:
                    continue
                # Ask dry run or real
                mode = questionary.select(
                    "Migration mode:",
                    choices=[
                        questionary.Choice(title="Dry run (no changes)", value='dry'),
                        questionary.Choice(title="Real migration", value='real'),
                        questionary.Choice(title="Cancel", value='cancel')
                    ],
                    qmark='🚚'
                ).ask()
                if mode in (None, 'cancel'):
                    continue
                dry_flag = ['--dry-run'] if mode == 'dry' else []
                # Optional custom GitHub repo name
                gh_custom = questionary.text("GitHub repository name (leave blank to use same name):").ask()
                gh_args = ['--github-repo', gh_custom] if gh_custom else []
                cmd = [sys.executable, '-m', 'azuredevops_github_migration', 'migrate', '--project', project, '--repo', repo, *dry_flag, *gh_args]
                print("Running:", ' '.join(cmd))
                subprocess.run(cmd)
            except Exception as e:
                print(f"Interactive migrate flow failed; falling back to basic migrate: {e}")
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'migrate'])
        elif key == 'analyze':
            # Enhanced analyze flow: choose single project (fast) or full org
            try:
                choice = questionary.select(
                    "Analyze scope:",
                    choices=[
                        questionary.Choice(title="Single project (faster)", value='single'),
                        questionary.Choice(title="Full organization (all projects & repos)", value='full'),
                        questionary.Choice(title="Cancel", value='cancel'),
                    ],
                    qmark='🔎'
                ).ask()
                if choice in (None, 'cancel'):
                    continue
                # Auto-detect skip-work-items flag (Jira template etc.)
                skip_flag = []
                try:
                    if os.path.exists('config.json'):
                        import json as _json
                        with open('config.json','r',encoding='utf-8') as _cf:
                            _cfg = _json.load(_cf)
                        if not _cfg.get('migration', {}).get('migrate_work_items', True):
                            skip_flag = ['--skip-work-items']
                except Exception:
                    pass
                if choice == 'full':
                    subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'analyze', '--create-plan', *skip_flag])
                else:
                    # Single project: fetch list then use picker
                    from .analyze import AzureDevOpsAnalyzer
                    analyzer = AzureDevOpsAnalyzer('config.json', skip_work_items=True, omit_work_item_fields=True)
                    projects = analyzer.client.get_projects()
                    names = sorted([p['name'] for p in projects], key=lambda s: s.lower())
                    if not names:
                        print("No projects found.")
                        continue
                    if len(names) == 1:
                        selected = names[0]
                    else:
                        selected = _paginated_picker("Select a project", names, allow_cancel=True)
                    if not selected:
                        continue
                    subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'analyze', '--project', selected, '--create-plan', *skip_flag])
            except Exception as e:
                print(f"Analyze interactive flow failed, falling back to default: {e}")
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'analyze'])
        elif key == 'batch':
            subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'batch'])
        elif key == 'doctor_menu':
            sub = questionary.select(
                "Doctor diagnostics:",
                choices=[
                    questionary.Choice(title="Run diagnostics (doctor)", value='plain'),
                    questionary.Choice(title="Enter / update environment variables (--edit-env)", value='edit_env'),
                    questionary.Choice(title="Append missing env placeholders (doctor --fix-env)", value='fix'),
                    questionary.Choice(title="Remediation assistant (--assist)", value='assist'),
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
            elif sub == 'edit_env':
                subprocess.run([sys.executable, '-m', 'azuredevops_github_migration', 'doctor', '--edit-env'])
            else:  # back or None
                continue
        elif key == 'quit':
            print("Exiting interactive menu.")
            break
    return 0


# === Enhanced selection helpers (borrowed/extended from quickstart) ===

def _fuzzy_filter(full_list: Sequence[str], text: str) -> List[str]:
    lower = text.lower()
    def fuzzy(name: str) -> bool:
        nlow = name.lower()
        if lower in nlow:
            return True
        idx = 0
        for ch in lower:
            idx = nlow.find(ch, idx)
            if idx == -1:
                return False
            idx += 1
        return True
    return [p for p in full_list if fuzzy(p)]


def _paginated_picker(
    title: str,
    items: Sequence[str],
    page_size: int = 10,
    allow_skip: bool = False,
    skip_label: str = 'Skip',
    allow_cancel: bool = True,
    jump_label: str = 'Jump to letter',
    search_label: str = 'Search / filter',
    clear_label: str = 'Clear filter',
    transform: Optional[Callable[[str], str]] = None,
) -> Optional[str]:
    """Generic paginated selector returning chosen item or None.

    Returns None on cancel or skip. (Caller can differentiate by allow_skip flag if needed.)
    """
    if not questionary:
        return None
    full_list = list(items)
    filtered = full_list
    filter_text = ''
    page = 0
    use_icons = os.getenv('MIGRATION_CLI_NO_ICONS','').lower() not in ('1','true','yes')

    def _nav(value: str, icon: str):
        if not use_icons:
            return value
        try:
            from questionary import Choice  # type: ignore
            return Choice(title=f"{icon} {value}", value=value)
        except Exception:  # pragma: no cover
            return value

    while True:
        total = len(filtered)
        if total == 0:
            q_choices = [
                '(No matches)',
                _nav(clear_label,'🧹'),
                _nav(search_label,'🔍'),
            ]
            if allow_skip:
                q_choices.append(_nav(skip_label,'⏭️'))
            if allow_cancel:
                q_choices.append(_nav('Cancel','🚫'))
            ans = questionary.select(f"No results for '{filter_text}'.", choices=q_choices, qmark='📁').ask()
            if ans == clear_label:
                filter_text = ''
                filtered = full_list
                page = 0
                continue
            if ans == search_label:
                s = questionary.text(f'{search_label}:').ask()
                if s:
                    filter_text = s
                    filtered = _fuzzy_filter(full_list, s)
                    page = 0
                continue
            if ans == skip_label:
                return None
            return None
        max_pages = (total + page_size - 1)//page_size
        if page >= max_pages:
            page = max_pages - 1 if max_pages>0 else 0
        start = page * page_size
        end = min(start + page_size, total)
        slice_choices = filtered[start:end]
        nav_choices: List[str] = []
        if page > 0:
            nav_choices.append(_nav('◀ Prev page','⬅️'))
        if end < total:
            nav_choices.append(_nav('Next page ▶','➡️'))
        nav_choices.append(_nav(search_label,'🔍'))
        if filter_text:
            nav_choices.append(_nav(clear_label,'🧹'))
        nav_choices.append(_nav(jump_label,'🔤'))
        if allow_skip:
            nav_choices.append(_nav(skip_label,'⏭️'))
        if allow_cancel:
            nav_choices.append(_nav('Cancel','🚫'))
        q_choices = list(slice_choices) + nav_choices
        prompt = f"{title} (page {page+1}/{max_pages})"
        if filter_text:
            prompt += f" [filter='{filter_text}']"
        ans = questionary.select(prompt + ':', choices=q_choices, qmark='📁').ask()
        if ans is None or ans == 'Cancel':
            return None
        if ans == '◀ Prev page':
            page = max(page-1,0)
            continue
        if ans == 'Next page ▶':
            if end < total:
                page += 1
            continue
        if ans == search_label:
            s = questionary.text(f'{search_label} (substring or fuzzy):').ask()
            if s:
                filter_text = s
                filtered = _fuzzy_filter(full_list, s)
                page = 0
            continue
        if ans == clear_label:
            filter_text = ''
            filtered = full_list
            page = 0
            continue
        if ans == jump_label:
            letter = questionary.text('Enter starting letter:').ask()
            if letter:
                l = letter[0].lower()
                idx = next((i for i,n in enumerate(filtered) if n.lower().startswith(l)), None)
                if idx is not None:
                    page = idx // page_size
            continue
        if ans == skip_label:
            return None
        # Otherwise selected item
        return transform(ans) if transform else ans
