#!/usr/bin/env python3
from __future__ import annotations
"""Batch migration with parallel execution, state tracking, and retry support."""

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from .migrate import MigrationOrchestrator
from .state import MigrationState


def load_migration_plan(file_path: str) -> List[Dict[str, Any]]:
    """Load migration plan from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def create_sample_migration_plan():
    """Create a sample migration plan file."""
    sample = [
        {
            "project_name": "MyProject",
            "repo_name": "my-first-repo",
            "github_repo_name": "migrated-first-repo",
            "migrate_issues": False,
            "description": "First repository to migrate",
        },
        {
            "project_name": "MyProject",
            "repo_name": "my-second-repo",
            "github_repo_name": "migrated-second-repo",
            "migrate_issues": False,
            "description": "Second repository - code only",
        },
    ]
    with open("migration_plan.json", "w") as f:
        json.dump(sample, f, indent=2)
    print("Sample migration plan created: migration_plan.json")


def _repo_key(entry: Dict[str, Any]) -> str:
    return f"{entry['project_name']}/{entry['repo_name']}"


def _should_migrate(entry: Dict[str, Any], state: MigrationState, retry_failed: bool) -> bool:
    """Determine if this repo should be migrated in this run."""
    key = _repo_key(entry)
    status = state.get_status(key)
    if status == "completed" or status == "skipped":
        return False
    if retry_failed:
        return status == "failed"
    return status in ("pending", "failed", None)


def _migrate_single(
    entry: Dict[str, Any],
    orchestrator: MigrationOrchestrator,
    state: MigrationState,
    dry_run: bool,
) -> bool:
    """Migrate a single repo. Updates state on success/failure."""
    key = _repo_key(entry)
    state.mark_in_progress(key, step="starting")
    try:
        success = orchestrator.migrate_repository(
            project_name=entry["project_name"],
            repo_name=entry["repo_name"],
            github_repo_name=entry.get("github_repo_name", entry["repo_name"]),
            migrate_issues=entry.get("migrate_issues", False),
            migrate_pipelines=entry.get("migrate_pipelines", False),
            dry_run=dry_run,
        )
        if success:
            github_org = orchestrator.config.get("github", {}).get("organization", "")
            gh_name = entry.get("github_repo_name", entry["repo_name"])
            state.mark_completed(key, github_url=f"https://github.com/{github_org}/{gh_name}")
        else:
            state.mark_failed(key, error="migrate_repository returned False")
        return success
    except Exception as e:
        state.mark_failed(key, error=str(e))
        return False


def run_batch_migration(
    plan: List[Dict[str, Any]],
    config_file: str,
    state: MigrationState,
    concurrency: int = 4,
    dry_run: bool = False,
    retry_failed: bool = False,
) -> Dict[str, bool]:
    """Run batch migration with parallel execution and state tracking."""
    # Register all repos in state
    for entry in plan:
        state.add_repo(_repo_key(entry))

    # Filter to repos that need migration
    to_migrate = [e for e in plan if _should_migrate(e, state, retry_failed)]

    if not to_migrate:
        print("No repos to migrate (all completed or skipped).")
        return {}

    orchestrator = MigrationOrchestrator(config_file)
    results: Dict[str, bool] = {}

    if concurrency <= 1:
        for entry in to_migrate:
            key = _repo_key(entry)
            results[key] = _migrate_single(entry, orchestrator, state, dry_run)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {}
            for entry in to_migrate:
                future = executor.submit(_migrate_single, entry, orchestrator, state, dry_run)
                futures[future] = _repo_key(entry)

            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = False
                    state.mark_failed(key, error=str(e))

    return results


def main(args=None):
    """Main entry point for batch migration."""
    parser = argparse.ArgumentParser(description="Batch Azure DevOps to GitHub Migration")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--plan", default="migration_plan.json", help="Migration plan JSON file")
    parser.add_argument("--state-file", default=None, help="State file for resume/tracking")
    parser.add_argument("--wave", default="default", help="Wave name for state tracking")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel migrations (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed repos")
    parser.add_argument("--create-sample", action="store_true", help="Create sample plan file")

    parsed = parser.parse_args(args)

    if parsed.create_sample:
        create_sample_migration_plan()
        return

    try:
        plan = load_migration_plan(parsed.plan)
        state_file = parsed.state_file or f"migration_state_{parsed.wave}.json"
        state = MigrationState(state_file, wave=parsed.wave)

        print(f"Batch migration: {len(plan)} repos, concurrency={parsed.concurrency}")
        if parsed.dry_run:
            print("DRY RUN MODE")

        results = run_batch_migration(
            plan, parsed.config, state,
            concurrency=parsed.concurrency,
            dry_run=parsed.dry_run,
            retry_failed=parsed.retry_failed,
        )

        total = len(results)
        success = sum(1 for v in results.values() if v)
        rate = (success / total * 100) if total > 0 else 100

        print(f"\nBatch complete: {rate:.1f}% ({success}/{total})")
        c = state.counts
        print(f"  Completed: {c['completed']}  Failed: {c['failed']}  Pending: {c['pending']}")

        if c["failed"] > 0:
            print("Use --retry-failed to retry failed repos.")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
