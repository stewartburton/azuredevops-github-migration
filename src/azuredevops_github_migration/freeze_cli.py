"""CLI wrappers for freeze/unfreeze commands."""
import argparse
import json
import sys
from .config import load_config
from .freeze import AdoRepoFreezer
from .state import MigrationState


def main(args=None):
    """Freeze repos in a migration plan."""
    parser = argparse.ArgumentParser(description="Freeze ADO repos")
    parser.add_argument("--plan", required=True, help="Migration plan JSON")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--state-file", default=None, help="State file to record freeze ACLs")
    parsed = parser.parse_args(args)

    config = load_config(parsed.config)
    freezer = AdoRepoFreezer(
        config["azure_devops"]["organization"],
        config["azure_devops"]["personal_access_token"],
    )

    with open(parsed.plan) as f:
        plan = json.load(f)

    state = MigrationState(parsed.state_file or "freeze_state.json", wave="freeze") if parsed.state_file else None

    for entry in plan:
        project = entry["project_name"]
        repo_name = entry["repo_name"]
        try:
            repo_id = freezer.resolve_repo_id(project, repo_name)
            result = freezer.freeze_repo(project, repo_id)
            if result["success"]:
                print(f"[FREEZE] {project}/{repo_name}")
                if state:
                    state.store_freeze_acls(f"{project}/{repo_name}", result["original_acls"])
            else:
                print(f"[FAIL]   {project}/{repo_name}: {result.get('error')}")
        except Exception as e:
            print(f"[ERROR]  {project}/{repo_name}: {e}")


def main_unfreeze(args=None):
    """Unfreeze repos using saved ACLs from state file."""
    parser = argparse.ArgumentParser(description="Unfreeze ADO repos")
    parser.add_argument("--plan", required=True, help="Migration plan JSON")
    parser.add_argument("--config", default="config.json", help="Config file")
    parser.add_argument("--state-file", required=True, help="State file with saved ACLs")
    parsed = parser.parse_args(args)

    config = load_config(parsed.config)
    freezer = AdoRepoFreezer(
        config["azure_devops"]["organization"],
        config["azure_devops"]["personal_access_token"],
    )
    state = MigrationState(parsed.state_file)

    with open(parsed.plan) as f:
        plan = json.load(f)

    for entry in plan:
        project = entry["project_name"]
        repo_name = entry["repo_name"]
        key = f"{project}/{repo_name}"
        acls = state.get_freeze_acls(key)
        if not acls:
            print(f"[SKIP] {key}: no saved ACLs")
            continue
        try:
            repo_id = freezer.resolve_repo_id(project, repo_name)
            result = freezer.unfreeze_repo(project, repo_id, acls)
            if result["success"]:
                print(f"[UNFREEZE] {key}")
            else:
                print(f"[FAIL]     {key}: {result.get('error')}")
        except Exception as e:
            print(f"[ERROR]    {key}: {e}")
