"""Quickstart workflow helper.

Performs a guided onboarding sequence:
    1. init (if needed)
    2. interactive environment entry (doctor --edit-env)
    3. doctor diagnostics (post-entry)
    4. analyze --list-projects (quick discovery)
    5. next-step recommendations

Usage:
  azuredevops-github-migration quickstart --template jira-users
  azuredevops-github-migration quickstart --skip-init
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional

try:
    import questionary  # type: ignore
except Exception:  # pragma: no cover
    questionary = None


def _print(msg):
    print(f"[QUICKSTART] {msg}")


def _module_main(mod, argv=None):
    return mod(argv or [])


def main(argv=None):
    parser = argparse.ArgumentParser("Quickstart helper")
    parser.add_argument('--template', choices=['jira-users','full'], default='jira-users',
                        help='Config template to use if initializing')
    parser.add_argument('--skip-init', action='store_true', help='Skip init even if config.json missing')
    parser.add_argument('--skip-env', action='store_true', help='Skip interactive environment variable entry')
    parser.add_argument('--no-analyze', action='store_true', help='Skip analyze listing step')
    parser.add_argument('--non-interactive', action='store_true', help='Do not prompt for confirmation between steps')
    parser.add_argument('--no-project-select', action='store_true', help='Disable interactive project selection even if questionary is installed')
    parser.add_argument('--open-menu', action='store_true', help='Launch interactive menu after quickstart completes (bypasses prompt)')
    parser.add_argument('--debug', action='store_true', help='Verbose logging (passes through)')
    args = parser.parse_args(argv)

    debug = args.debug or os.environ.get('MIGRATION_DEBUG') == '1'

    start = datetime.now()
    _print(f"Starting quickstart at {start.isoformat()} (template={args.template})")

    # 1. init
    if not args.skip_init and not os.path.exists('config.json'):
        _print("Initializing configuration (config.json not found)...")
        try:
            from .init import main as init_main
            init_args = ['--template', args.template]
            if debug and '--debug' not in init_args:
                init_args.append('--debug')
            rc = init_main(init_args)
            if rc != 0:
                _print(f"Init failed with exit code {rc}; aborting")
                return rc
        except Exception as e:
            _print(f"Init step error: {e}")
            return 1
    else:
        _print("Skipping init (config.json present or --skip-init specified)")

    # Auto-patch config.json placeholders for organization keys if still template value
    try:
        if os.path.exists('config.json'):
            with open('config.json','r',encoding='utf-8') as f:
                cfg = json.load(f)
            changed = False
            ad_org = cfg.get('azure_devops', {}).get('organization')
            gh_org = cfg.get('github', {}).get('organization')
            # Placeholder detection list includes legacy hard-coded default and generic sample
            placeholder_tokens = {'your-organization-name','your-github-org','your_azure_devops_org_here','your_github_org_here'}
            env_ad = os.getenv('AZURE_DEVOPS_ORGANIZATION') or os.getenv('AZURE_DEVOPS_ORG')
            env_gh = os.getenv('GITHUB_ORGANIZATION') or os.getenv('GITHUB_ORG')
            if ad_org in placeholder_tokens and env_ad:
                cfg.setdefault('azure_devops', {})['organization'] = env_ad
                changed = True
                _print(f"Patched azure_devops.organization -> {env_ad} (from environment)")
            if gh_org in placeholder_tokens and env_gh:
                cfg.setdefault('github', {})['organization'] = env_gh
                changed = True
                _print(f"Patched github.organization -> {env_gh} (from environment)")
            if changed:
                # Backup original
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                try:
                    os.replace('config.json', f'config.json.bak.{ts}')
                    with open('config.json','w',encoding='utf-8') as f:
                        json.dump(cfg,f,indent=2)
                    _print(f"Updated config.json (backup saved as config.json.bak.{ts})")
                except Exception as be:
                    _print(f"Failed to write patched config.json: {be}")
    except Exception as e:
        if debug:
            _print(f"Config auto-patch warning: {e}")

    def _confirm(step: str) -> bool:
        if args.non_interactive:
            return True
        try:
            resp = input(f"Proceed with {step}? [Y/n]: ").strip().lower()
            return resp in ('', 'y', 'yes')
        except EOFError:
            return True

    # 2. environment entry (edit-env)
    if not args.skip_env:
        if _confirm('environment variable entry (doctor --edit-env)'):
            try:
                from .doctor import main as doctor_main
                _print("Launching interactive environment editor (doctor --edit-env)...")
                rc = doctor_main(['--edit-env'])
                if rc not in (0, 1):  # editor returns 0 normally; 1 may signify missing tokens yet
                    _print(f"Environment edit returned code {rc}")
            except Exception as e:
                _print(f"Environment edit error: {e}")
        else:
            _print("Skipped interactive environment entry by user choice")
    else:
        _print("Skipping environment entry (--skip-env)")

    # 3. doctor diagnostics (post env)
    try:
        _print("Running doctor diagnostics...")
        from .doctor import main as doctor_main
        rc = doctor_main(['--config','config.json'])
        if rc != 0:
            _print("Doctor reported issues (see above). You may continue, but address critical errors first.")
    except Exception as e:
        _print(f"Doctor step error: {e}")

    selected_project: Optional[str] = None
    project_names: list[str] = []
    force_launch_menu = False  # set when user chooses Skip during project selection

    # 4. analyze list projects (with optional interactive selection)
    if not args.no_analyze:
        try:
            _print("Listing projects (analyze --list-projects)...")
            # Instead of shelling entirely, reuse analyzer for programmatic list
            from .analyze import AzureDevOpsAnalyzer
            try:
                analyzer = AzureDevOpsAnalyzer('config.json', skip_work_items=True, omit_work_item_fields=True)
                projects = analyzer.client.get_projects()
                project_names = sorted([p['name'] for p in projects], key=lambda s: s.lower())
                total_projects = len(project_names)
                print(f"Found {total_projects} projects.")
                # Only print inline list if total <= page size threshold; otherwise rely on paginator
                page_size = 10
                if total_projects and total_projects <= page_size:
                    for name in project_names:
                        print(f"• {name}")

                # Interactive selection with pagination
                can_select = (not args.non_interactive) and (not args.no_project_select) and questionary is not None and project_names
                if can_select and project_names:
                    if len(project_names) == 1:
                        selected_project = project_names[0]
                    else:
                        try:
                            # page_size defined above; reuse
                            full_list = project_names
                            filtered = full_list
                            filter_text = ''
                            page = 0
                            def _apply_filter(txt: str):
                                lower = txt.lower()
                                # simple fuzzy: all chars must appear in order OR substring match
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
                            while True:
                                total = len(filtered)
                                if total == 0:
                                    # Navigation/icon helpers
                                    use_icons = os.getenv('MIGRATION_NO_NAV_ICONS','').lower() not in ('1','true','yes')
                                    def _nav(value: str, icon: str):
                                        if not use_icons:
                                            return value
                                        try:
                                            from questionary import Choice  # type: ignore
                                            return Choice(title=f"{icon} {value}", value=value)
                                        except Exception:  # pragma: no cover
                                            return value
                                    q_choices = [
                                        '(No matches)',
                                        _nav('Clear filter','🧹'),
                                        _nav('New search','🔍'),
                                        _nav('Skip (open interactive menu)','⏭️'),
                                        _nav('Cancel selection','🚫')
                                    ]
                                    ans = questionary.select(f"No results for '{filter_text}'.", choices=q_choices, qmark='📁').ask()
                                    if ans == 'Clear filter':
                                        filter_text = ''
                                        filtered = full_list
                                        page = 0
                                        continue
                                    if ans == 'New search':
                                        s = questionary.text('Search projects (substring or fuzzy):').ask()
                                        if s:
                                            filter_text = s
                                            filtered = _apply_filter(s)
                                            page = 0
                                        continue
                                    if ans == 'Skip (open interactive menu)':
                                        force_launch_menu = True
                                        break
                                    break
                                max_pages = (total + page_size - 1)//page_size
                                if page >= max_pages:
                                    page = max_pages - 1 if max_pages>0 else 0
                                start = page * page_size
                                end = min(start + page_size, total)
                                slice_choices = filtered[start:end]
                                use_icons = os.getenv('MIGRATION_NO_NAV_ICONS','').lower() not in ('1','true','yes')
                                def _nav(value: str, icon: str):
                                    if not use_icons:
                                        return value
                                    try:
                                        from questionary import Choice  # type: ignore
                                        return Choice(title=f"{icon} {value}", value=value)
                                    except Exception:  # pragma: no cover
                                        return value
                                nav_choices = []  # type: ignore[var-annotated]
                                if page > 0:
                                    nav_choices.append(_nav('◀ Prev page','⬅️'))
                                if end < total:
                                    nav_choices.append(_nav('Next page ▶','➡️'))
                                nav_choices.append(_nav('Search / filter','🔍'))
                                if filter_text:
                                    nav_choices.append(_nav('Clear filter','🧹'))
                                nav_choices.append(_nav('Jump to letter','🔤'))
                                nav_choices.append(_nav('Skip (open interactive menu)','⏭️'))
                                nav_choices.append(_nav('Cancel selection','🚫'))
                                q_choices = slice_choices + nav_choices
                                prompt = f"Select a project (page {page+1}/{max_pages})"
                                if filter_text:
                                    prompt += f" [filter='{filter_text}']"
                                ans = questionary.select(prompt + ':', choices=q_choices, qmark='📁').ask()
                                if ans is None or ans == 'Cancel selection':
                                    break
                                if ans == '◀ Prev page':
                                    page = max(page-1,0)
                                    continue
                                if ans == 'Next page ▶':
                                    if end < total:
                                        page += 1
                                    continue
                                if ans == 'Search / filter':
                                    s = questionary.text('Search projects (substring or fuzzy):').ask()
                                    if s:
                                        filter_text = s
                                        filtered = _apply_filter(s)
                                        page = 0
                                    continue
                                if ans == 'Clear filter':
                                    filter_text = ''
                                    filtered = full_list
                                    page = 0
                                    continue
                                if ans == 'Jump to letter':
                                    letter = questionary.text('Enter starting letter:').ask()
                                    if letter:
                                        l = letter[0].lower()
                                        # find first index in full_list (not filtered) to preserve global navigation
                                        target_list = filtered
                                        idx = next((i for i,n in enumerate(target_list) if n.lower().startswith(l)), None)
                                        if idx is not None:
                                            page = idx // page_size
                                    continue
                                if ans == 'Skip (open interactive menu)':
                                    force_launch_menu = True
                                    selected_project = None
                                    break
                                # Otherwise project
                                selected_project = ans
                                break
                        except Exception as qe:  # pragma: no cover
                            _print(f"Project selection skipped (UI error: {qe})")
                else:
                    if questionary is None and not args.non_interactive and not args.no_project_select:
                        _print("(Install 'questionary' for interactive project selection: pip install questionary)")
            except Exception as inner:
                _print(f"Analyze listing error: {inner}")
        except Exception as e:
            _print(f"Analyze listing error: {e}")
    else:
        _print("Skipping analyze listing (--no-analyze)")

    # 5. recommendations
    proj_token = selected_project or '<Project>'
    if ' ' in proj_token:
        proj_token_disp = f'"{proj_token}"'
    else:
        proj_token_disp = proj_token
    # If user chose Skip → open interactive menu immediately (bypass recommendations)
    if force_launch_menu:
        try:
            from .interactive import interactive_menu
            _print("Opening interactive menu (Skip chosen)...")
            interactive_menu()
        except Exception as e:  # pragma: no cover
            _print(f"Could not open interactive menu: {e}")
        return 0

    _print("Quickstart complete. Recommended next commands:")
    if selected_project:
        _print(f"  1) Analyze selected project: azuredevops-github-migration analyze --project {proj_token_disp} --create-plan")
        _print("     (Full org analysis: azuredevops-github-migration analyze --create-plan)")
    else:
        _print("  1) Analyze a single project (replace <Project>): azuredevops-github-migration analyze --project <Project> --create-plan")
        _print("     (Full org analysis is heavier; run only when needed: azuredevops-github-migration analyze --create-plan)")
    _print(f"  2) Dry run a repository: azuredevops-github-migration migrate --project {proj_token_disp} --repo <Repo> --dry-run --config config.json")
    _print(f"  3) Real migration: azuredevops-github-migration migrate --project {proj_token_disp} --repo <Repo> --config config.json")
    _print("  4) Batch (when ready): azuredevops-github-migration batch --plan migration_plan_<org>_*.json")
    if selected_project:
        _print(f"(Project '{selected_project}' selected for examples. Use --no-project-select to suppress.)")
    _print("Use 'doctor' anytime to re-check environment or placeholders.")

    # Optional interactive menu launch
    launch_menu = False
    if args.open_menu:
        launch_menu = True
    elif (not args.non_interactive):
        try:
            resp = input("Open interactive menu now? [Y/n]: ").strip().lower()
            if resp in ('', 'y', 'yes'):
                launch_menu = True
        except EOFError:
            pass

    if launch_menu:
        try:
            from .interactive import interactive_menu
            _print("Launching interactive menu...")
            interactive_menu()
        except Exception as e:  # pragma: no cover
            _print(f"Could not open interactive menu: {e}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())