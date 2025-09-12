#!/usr/bin/env python3
"""Diagnostic command (doctor) for Azure DevOps to GitHub Migration Tool.

Provides quick environment and configuration health checks to help users
troubleshoot installation or runtime issues.
"""

from __future__ import annotations

import os
import json
import shutil
import socket
import platform
import argparse
import subprocess
from pathlib import Path

# --- Internal helpers for optional .env loading (mirrors migrate/analyze behavior) ---
def _load_env_file(filename: str = '.env') -> None:
    """Load simple KEY=VALUE pairs from a .env file if present.

    This allows `doctor` to report token presence without requiring the user
    to manually export environment variables first. Intentionally lightweight
    (no extra dependency) and ignores malformed lines.
    """
    try:
        if not os.path.exists(filename):
            return
        with open(filename, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                # Do not overwrite if already set in environment
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:  # pragma: no cover - non critical path
        print(f"[WARN] Unable to load .env file: {e}")
from typing import Dict, Any

try:  # Local imports guarded so doctor works even if partial install
    from . import __version__
except Exception:  # pragma: no cover
    __version__ = "unknown"


def check_python() -> Dict[str, Any]:
    import sys
    return {
        "executable": sys.executable,
        "version": sys.version,
        "cwd": os.getcwd(),
        "path_entries": len(sys.path),
    }


def check_package_import() -> Dict[str, Any]:
    result: Dict[str, Any] = {"importable": True}
    try:
        import azuredevops_github_migration  # noqa: F401
    except Exception as e:  # pragma: no cover - only hit on broken installs
        result["importable"] = False
        result["error"] = str(e)
    return result


def check_git() -> Dict[str, Any]:
    import subprocess
    info: Dict[str, Any] = {"found": False}
    git_path = shutil.which("git")
    if git_path:
        info["found"] = True
        info["path"] = git_path
        try:
            out = subprocess.run([git_path, "--version"], capture_output=True, text=True, timeout=10)
            info["version_output"] = out.stdout.strip() or out.stderr.strip()
        except Exception as e:  # pragma: no cover
            info["error"] = str(e)
    return info


def check_network_host(host: str, port: int = 443, timeout: float = 2.5) -> Dict[str, Any]:
    s = socket.socket()
    s.settimeout(timeout)
    result = {"host": host, "port": port, "reachable": False}
    try:
        s.connect((host, port))
        result["reachable"] = True
    except Exception as e:  # pragma: no cover
        result["error"] = str(e)
    finally:
        try:
            s.close()
        except Exception:
            pass
    return result


def check_config_file(config_path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"exists": os.path.exists(config_path), "path": config_path}
    if data["exists"]:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.endswith(".json"):
                    json.load(f)
                else:
                    try:
                        import yaml  # type: ignore
                    except ImportError:
                        data["parse_ok"] = False
                        data["error"] = (
                            "PyYAML is required to parse YAML config files. "
                            "Please install it with 'pip install pyyaml'."
                        )
                        return data
                    yaml.safe_load(f)
            data["parse_ok"] = True
        except Exception as e:
            data["parse_ok"] = False
            data["error"] = str(e)
    return data


PLACEHOLDER_PREFIXES = (
    'your_azure_devops_personal_access_token',
    'your_github_personal_access_token',
    'your_azure_devops_org',
    'your_github_org'
)


def _gather_env_audit() -> Dict[str, Any]:
    """Collect environment variable audit similar to Test-MigrationEnv.ps1 (lightweight).

    We consider both canonical and legacy aliases; we don't mutate env here beyond
    prior optional .env loading. Values are masked in output.
    """
    def mask(val: str | None) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return f"{val[:4]}...{val[-4:]}"

    aliases = {
        "AZURE_DEVOPS_ORGANIZATION": ["AZURE_DEVOPS_ORGANIZATION", "AZURE_DEVOPS_ORG"],
        "GITHUB_ORGANIZATION": ["GITHUB_ORGANIZATION", "GITHUB_ORG"],
        "AZURE_DEVOPS_PAT": ["AZURE_DEVOPS_PAT"],
        "GITHUB_TOKEN": ["GITHUB_TOKEN"],
    }
    audit: Dict[str, Any] = {"variables": {}, "all_present": True}
    for canon, keys in aliases.items():
        raw_value = None
        for k in keys:
            if k in os.environ:
                raw_value = os.environ.get(k)
                break
        placeholder = False
        if raw_value:
            lower = raw_value.lower()
            for p in PLACEHOLDER_PREFIXES:
                if lower.startswith(p):
                    placeholder = True
                    break
        audit["variables"][canon] = {
            "present": bool(raw_value),
            "masked": mask(raw_value),
            "aliases_checked": keys,
            "placeholder": placeholder,
        }
        if not raw_value:
            audit["all_present"] = False
        elif placeholder:
            # treat placeholder as a not-usable value for overall readiness
            audit.setdefault('placeholders', []).append(canon)
    return audit


def _append_missing_env_placeholders(env_path: str, audit: Dict[str, Any]) -> Dict[str, Any]:
    """Append placeholder lines for any missing canonical env variables.

    Does not overwrite existing lines; only appends. Returns a dict with keys:
    {added: [names], path: env_path}
    """
    canonical_order = [
        ("AZURE_DEVOPS_PAT", "your_azure_devops_personal_access_token_here"),
        ("GITHUB_TOKEN", "your_github_personal_access_token_here"),
        ("AZURE_DEVOPS_ORGANIZATION", "your_azure_devops_org_here"),
        ("GITHUB_ORGANIZATION", "your_github_org_here"),
    ]
    added: list[str] = []
    # Ensure file exists
    path = Path(env_path)
    existing_lower = set()
    if path.exists():
        try:
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        existing_lower.add(line.split('=',1)[0].strip().lower())
        except Exception:  # pragma: no cover - non critical
            pass
    else:
        # Create an empty file so we can append
        path.touch()
    try:
        with path.open('a', encoding='utf-8') as f:
            for name, placeholder in canonical_order:
                canon_present = audit['variables'][name]['present']
                # consider alias presence as present for skip? we still want canonical line if alias only
                # Add if canonical missing (no exact case-insensitive match for name)
                if not canon_present and name.lower() not in existing_lower:
                    f.write(f"{name}={placeholder}\n")
                    added.append(name)
    except Exception as e:  # pragma: no cover
        return {"added": added, "path": env_path, "error": str(e)}
    return {"added": added, "path": env_path}


def gather_diagnostics(config: str, fix_env: bool = False) -> Dict[str, Any]:
    # Attempt to load .env early so presence test reflects file contents
    _load_env_file()
    env_audit = _gather_env_audit()
    diag: Dict[str, Any] = {
        "tool_version": __version__,
        "platform": platform.platform(),
        "python": check_python(),
        "package_import": check_package_import(),
        "git": check_git(),
        "config": check_config_file(config),
        "network": {
            "github_api": check_network_host("api.github.com"),
            "azure_devops": check_network_host("dev.azure.com"),
        },
        "env": env_audit,
    }
    if fix_env:
        diag["fix_env"] = _append_missing_env_placeholders('.env', env_audit)
    return diag


def print_human(diag: Dict[str, Any]):
    print("Azure DevOps → GitHub Migration Tool Diagnostics")
    print("=" * 60)
    print(f"Version: {diag['tool_version']}")
    print(f"Platform: {diag['platform']}")
    print("Python:")
    print(f"  Executable: {diag['python']['executable']}")
    print(f"  Version: {diag['python']['version'].splitlines()[0]}")
    print(f"  sys.path entries: {diag['python']['path_entries']}")
    print("Package Import:")
    if diag['package_import']['importable']:
        print("  Status: OK (module importable)")
    else:
        print("  Status: FAIL")
        print(f"  Error: {diag['package_import'].get('error')}")
    print("Git:")
    if diag['git']['found']:
        print(f"  Found: {diag['git']['path']}")
        print(f"  Version: {diag['git'].get('version_output','?')}")
    else:
        print("  Not found in PATH – required for migrations")
    print("Config:")
    if diag['config']['exists']:
        status = "OK" if diag['config'].get('parse_ok') else 'PARSE ERROR'
        print(f"  {diag['config']['path']} → {status}")
        if diag['config'].get('error'):
            print(f"  Error: {diag['config']['error']}")
    else:
        print(f"  Missing: {diag['config']['path']}")
    print("Environment Variables:")
    for name, meta in diag['env']['variables'].items():
        status = 'SET' if meta['present'] else 'MISSING'
        masked = meta['masked'] or '-'
        print(f"  {name}: {status}  (value: {masked})")
    if not diag['env']['all_present']:
        print("  One or more required variables are missing. Run: scripts/Test-MigrationEnv.ps1 -Load")
    print("Network Reachability (TCP 443):")
    for name, res in diag['network'].items():
        if res['reachable']:
            print(f"  {name}: reachable")
        else:
            print(f"  {name}: UNREACHABLE ({res.get('error','?')})")
    print("=" * 60)
    if not diag['package_import']['importable']:
        print("Package import failed — try reinstall: pip install --force-reinstall azuredevops-github-migration")
    if not diag['git']['found']:
        print("Install Git and ensure it is on your PATH.")
    if not diag['config']['exists']:
        print("Initialize a config: azuredevops-github-migration init --template jira-users")


def _assist_loop(config: str):
    """Interactive remediation submenu for doctor.

    Provides options:
      1. Run PowerShell env loader (update-env)
      2. Append missing placeholders (fix-env)
      3. Re-run diagnostics
      4. Quit
    """
    from .interactive import run_update_env  # local import to avoid heavy dependency if unused
    while True:
        diag = gather_diagnostics(config)
        print("\nCurrent environment status:")
        for name, meta in diag['env']['variables'].items():
            state = 'OK'
            if not meta['present']:
                state = 'MISSING'
            elif meta.get('placeholder'):
                state = 'PLACEHOLDER'
            print(f"  - {name}: {state} (value: {meta['masked'] or '-'})")
        if diag['env'].get('placeholders'):
            print(f"Placeholders detected for: {', '.join(diag['env']['placeholders'])}")
        print("\nRemediation options:")
        print("  1) Run PowerShell helper to load/update env (update-env)")
        print("  2) Append missing canonical placeholders (fix-env)")
        print("  3) Re-run diagnostics (refresh)")
        print("  4) Quit assist menu")
        choice = input("Select option [1-4]: ").strip()
        if choice == '1':
            rc = run_update_env()
            print(f"update-env exit code: {rc}")
        elif choice == '2':
            new_diag = gather_diagnostics(config, fix_env=True)
            added = new_diag.get('fix_env', {}).get('added', [])
            if added:
                print(f"Added placeholders for: {', '.join(added)}")
            else:
                print("No new placeholders added (all present).")
        elif choice == '3':
            continue  # loop reruns diagnostics
        elif choice == '4':
            print("Exiting assist submenu.")
            break
        else:
            print("Invalid selection – choose 1, 2, 3, or 4.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnostic utility for migration tool")
    parser.add_argument('--config', default='config.json', help='Config file to validate (json or yaml)')
    parser.add_argument('--json', action='store_true', help='Output JSON only (machine-readable)')
    parser.add_argument('--fix-env', action='store_true', help='Append missing canonical env variable placeholders to .env')
    parser.add_argument('--assist', action='store_true', help='Open interactive remediation submenu after diagnostics')
    args = parser.parse_args(argv)
    diag = gather_diagnostics(args.config, fix_env=args.fix_env)
    if args.json:
        print(json.dumps(diag, indent=2))
    else:
        print_human(diag)
        if args.fix_env and 'fix_env' in diag:
            added = diag['fix_env'].get('added', [])
            if added:
                print(f"Appended placeholders for: {', '.join(added)} → .env")
            else:
                if diag['fix_env'].get('error'):
                    print(f"Failed to append placeholders: {diag['fix_env']['error']}")
                else:
                    print("All canonical environment variable placeholders already present.")
        if args.assist and not args.json:
            _assist_loop(args.config)
    # Exit non-zero if critical failures
    critical_fail = (
        (not diag['package_import']['importable'])
        or (not diag['git']['found'])
        or (not diag['env']['variables']['AZURE_DEVOPS_PAT']['present'])
        or (not diag['env']['variables']['GITHUB_TOKEN']['present'])
    )
    return 1 if critical_fail else 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())