#!/usr/bin/env python3
"""
Batch migration script for migrating multiple repositories from Azure DevOps to GitHub.
"""

import json
import logging
from typing import Dict, List, Any
from migrate import MigrationOrchestrator
from utils import log_migration_summary


def load_migration_plan(file_path: str) -> List[Dict[str, Any]]:
    """Load migration plan from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def create_sample_migration_plan():
    """Create a sample migration plan file."""
    sample_plan = [
        {
            "project_name": "MyProject",
            "repo_name": "my-first-repo",
            "github_repo_name": "migrated-first-repo",
            "migrate_issues": True,
            "description": "First repository to migrate"
        },
        {
            "project_name": "MyProject",
            "repo_name": "my-second-repo",
            "github_repo_name": "migrated-second-repo",
            "migrate_issues": False,
            "description": "Second repository - code only"
        }
    ]
    
    with open('migration_plan.json', 'w') as f:
        json.dump(sample_plan, f, indent=2)
    
    print("✅ Sample migration plan created: migration_plan.json")
    print("Edit this file to specify your repositories to migrate.")


def main():
    """Main entry point for batch migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Azure DevOps to GitHub Migration')
    parser.add_argument('--config', default='migration_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--plan', default='migration_plan.json',
                       help='Migration plan JSON file')
    parser.add_argument('--create-sample', action='store_true',
                       help='Create a sample migration plan file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without actually doing it')
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_migration_plan()
        return
    
    try:
        # Load migration plan
        migration_plan = load_migration_plan(args.plan)
        
        if args.dry_run:
            print("🔍 DRY RUN - Showing migration plan:")
            print("=" * 50)
            for i, migration in enumerate(migration_plan, 1):
                print(f"{i}. {migration['project_name']}/{migration['repo_name']}")
                print(f"   → GitHub: {migration.get('github_repo_name', migration['repo_name'])}")
                print(f"   → Migrate Issues: {migration.get('migrate_issues', True)}")
                if migration.get('description'):
                    print(f"   → Description: {migration['description']}")
                print()
            print(f"Total repositories to migrate: {len(migration_plan)}")
            return
        
        # Initialize orchestrator
        orchestrator = MigrationOrchestrator(args.config)
        
        print(f"🚀 Starting batch migration of {len(migration_plan)} repositories...")
        
        # Perform migrations
        results = {}
        for i, migration in enumerate(migration_plan, 1):
            project_name = migration['project_name']
            repo_name = migration['repo_name']
            github_repo_name = migration.get('github_repo_name', repo_name)
            migrate_issues = migration.get('migrate_issues', True)
            
            print(f"\n[{i}/{len(migration_plan)}] Migrating {project_name}/{repo_name}...")
            
            success = orchestrator.migrate_repository(
                project_name,
                repo_name,
                github_repo_name,
                migrate_issues
            )
            
            results[f"{project_name}/{repo_name}"] = success
            
            if success:
                print(f"✅ Successfully migrated {project_name}/{repo_name}")
            else:
                print(f"❌ Failed to migrate {project_name}/{repo_name}")
        
        # Log summary
        log_migration_summary(results, orchestrator.logger)
        
        # Calculate success rate
        total = len(results)
        successful = sum(1 for success in results.values() if success)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"\n🎯 Batch migration completed!")
        print(f"Success rate: {success_rate:.1f}% ({successful}/{total})")
        
        if successful < total:
            print("⚠️  Some migrations failed. Check the logs for details.")
            exit(1)
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {str(e)}")
        if 'migration_plan.json' in str(e):
            print("💡 Use --create-sample to create a sample migration plan.")
        exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()