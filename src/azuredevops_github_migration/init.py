#!/usr/bin/env python3
"""
Initialization module for setting up configuration templates
"""

import os
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

def create_jira_config() -> Dict[str, Any]:
    """Create configuration optimized for Jira users."""
    return {
        "azure_devops": {
            "organization": "${AZURE_DEVOPS_ORGANIZATION}",
            "personal_access_token": "${AZURE_DEVOPS_PAT}",
            "project": "your-project-name"
        },
        "github": {
            "token": "${GITHUB_TOKEN}",
            "organization": "${GITHUB_ORGANIZATION}",
            "create_private_repos": True
        },
        "migration": {
            "_comment": "Optimized for Jira users - only migrates Git repositories and pipelines",
            "migrate_work_items": False,
            "migrate_pull_requests": False,
            "batch_size": 100,
            "delay_between_requests": 0.5,
            "max_retries": 3,
            "include_closed_work_items": False
        },
        "rate_limiting": {
            "azure_devops_requests_per_second": 10,
            "github_requests_per_second": 30,
            "enable_backoff": True,
            "backoff_factor": 2.0
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "migration.log",
            "console": True
        },
        "output": {
            "generate_reports": True,
            "report_format": "json",
            "output_directory": "./migration_reports",
            "include_statistics": True
        }
    }

def create_full_config() -> Dict[str, Any]:
    """Create configuration for complete migration including work items."""
    return {
        "azure_devops": {
            "organization": "${AZURE_DEVOPS_ORGANIZATION}",
            "personal_access_token": "${AZURE_DEVOPS_PAT}",
            "project": "your-project-name"
        },
        "github": {
            "token": "${GITHUB_TOKEN}",
            "organization": "${GITHUB_ORGANIZATION}",
            "create_private_repos": True
        },
        "migration": {
            "migrate_work_items": True,
            "migrate_pull_requests": False,
            "batch_size": 50,
            "delay_between_requests": 1.0,
            "max_retries": 3,
            "include_closed_work_items": True
        },
        "work_item_mapping": {
            "type_mappings": {
                "User Story": "enhancement",
                "Bug": "bug",
                "Task": "task",
                "Epic": "epic"
            },
            "state_mappings": {
                "New": "open",
                "Active": "open", 
                "Resolved": "closed",
                "Closed": "closed"
            },
            "priority_mappings": {
                "1": "critical",
                "2": "high",
                "3": "medium",
                "4": "low"
            }
        },
        "rate_limiting": {
            "azure_devops_requests_per_second": 5,
            "github_requests_per_second": 20,
            "enable_backoff": True,
            "backoff_factor": 2.0
        },
        "logging": {
            "level": "INFO", 
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "migration.log",
            "console": True
        },
        "output": {
            "generate_reports": True,
            "report_format": "json",
            "output_directory": "./migration_reports",
            "include_statistics": True
        }
    }

def create_env_template() -> str:
    """Create .env file template."""
    return """# Azure DevOps to GitHub Migration Tool - Environment Variables
# 
# Instructions:
# 1. Replace the placeholder values below with your actual tokens
# 2. Keep this file secure and never commit it to version control
# 3. Ensure .env is listed in your .gitignore file

# Azure DevOps Personal Access Token
# Create at: https://dev.azure.com/{org}/_usersSettings/tokens
# Required scopes: Code (Read), Project and Team (Read) 
# Optional: Work Items (Read) - only if migrating work items to GitHub Issues
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token_here

# GitHub Personal Access Token  
# Create at: https://github.com/settings/tokens
# Required scopes: repo
# Optional: admin:org - only if tool needs to create repositories
GITHUB_TOKEN=your_github_personal_access_token_here

# Azure DevOps organization slug (no URL). Alias also accepted: AZURE_DEVOPS_ORG
AZURE_DEVOPS_ORGANIZATION=your_azure_devops_org_here

# GitHub organization or user owner (destination). Alias accepted: GITHUB_ORG
GITHUB_ORGANIZATION=your_github_org_here

# Optional: Custom API endpoints (usually not needed)
# AZURE_DEVOPS_BASE_URL=https://dev.azure.com
# GITHUB_BASE_URL=https://api.github.com
"""

def init_config(template: str = "jira-users", force: bool = False) -> bool:
    """Initialize configuration files."""
    
    config_file = "config.json"
    env_file = ".env"
    
    # Check if files already exist
    if os.path.exists(config_file) and not force:
        print(f"❌ {config_file} already exists. Use --force to overwrite.")
        return False
        
    if os.path.exists(env_file) and not force:
        print(f"❌ {env_file} already exists. Use --force to overwrite.")
        return False
    
    try:
        # Create config based on template
        if template == "jira-users":
            config = create_jira_config()
            print("📝 Creating Jira users configuration (work items disabled)...")
        elif template == "full":
            config = create_full_config() 
            print("📝 Creating full migration configuration (including work items)...")
        else:
            print(f"❌ Unknown template: {template}")
            print("Available templates: jira-users, full")
            return False
        
        # Write config file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Created {config_file}")
        
        # Write .env template
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(create_env_template())
        print(f"✅ Created {env_file}")
        
        # Create reports directory
        os.makedirs("migration_reports", exist_ok=True)
        print("✅ Created migration_reports directory")
        
        # Print next steps
        print("\n🎉 Initialization completed successfully!")
        print("\n📝 Next Steps:")
        print(f"1. Edit {config_file} with your Azure DevOps and GitHub settings")
        print(f"2. Edit {env_file} with your personal access tokens")
        print("3. Run: azuredevops-github-migration migrate --validate-only --config config.json")
        print("\n📚 Documentation: https://github.com/stewartburton/azuredevops-github-migration/blob/main/docs/user-guide/HOW_TO_GUIDE.md")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return False

def main(args: Optional[list] = None):
    """Main entry point for init command."""
    parser = argparse.ArgumentParser(
        description="Initialize Azure DevOps to GitHub Migration Tool configuration"
    )
    parser.add_argument(
        "--template", 
        choices=["jira-users", "full"],
        default="jira-users",
        help="Configuration template to use (default: jira-users)"
    )
    parser.add_argument(
        "--force",
        action="store_true", 
        help="Overwrite existing configuration files"
    )
    
    if args is None:
        args = sys.argv[1:]
        
    parsed_args = parser.parse_args(args)
    
    success = init_config(parsed_args.template, parsed_args.force)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())