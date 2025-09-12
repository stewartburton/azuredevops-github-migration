"""Quickstart workflow helper.

Performs a minimal guided sequence:
  1. init (optional if config exists)
  2. doctor (environment diagnostics)
  3. analyze --list-projects (quick discovery)

Usage:
  azuredevops-github-migration quickstart --template jira-users
  azuredevops-github-migration quickstart --skip-init
"""

import os
import sys
import json
import argparse
from datetime import datetime


def _print(msg):
    print(f"[QUICKSTART] {msg}")


def _module_main(mod, argv=None):
    return mod(argv or [])


def main(argv=None):
    parser = argparse.ArgumentParser("Quickstart helper")
    parser.add_argument('--template', choices=['jira-users','full'], default='jira-users',
                        help='Config template to use if initializing')
    parser.add_argument('--skip-init', action='store_true', help='Skip init step even if config.json missing')
    parser.add_argument('--no-analyze', action='store_true', help='Skip analyze listing step')
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

    # 2. doctor
    try:
        _print("Running doctor diagnostics...")
        from .doctor import main as doctor_main
        rc = doctor_main(['--config','config.json'])
        if rc != 0:
            _print("Doctor reported issues (see above). You may continue, but address critical errors first.")
    except Exception as e:
        _print(f"Doctor step error: {e}")

    # 3. analyze list projects
    if not args.no_analyze:
        try:
            _print("Listing projects (analyze --list-projects)...")
            from .analyze import main as analyze_main
            a_args = ['--list-projects']
            if debug:
                a_args.insert(0,'--debug')
            analyze_main(a_args)
        except Exception as e:
            _print(f"Analyze listing error: {e}")
    else:
        _print("Skipping analyze listing (--no-analyze)")

    _print("Quickstart complete. Next typical command:")
    _print("  azuredevops-github-migration analyze --create-plan")
    _print("Then dry-run a repo:")
    _print("  azuredevops-github-migration migrate --project <Project> --repo <Repo> --dry-run --config config.json")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())