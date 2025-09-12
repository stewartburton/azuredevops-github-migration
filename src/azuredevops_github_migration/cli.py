#!/usr/bin/env python3
"""
Command Line Interface for Azure DevOps to GitHub Migration Tool
"""

import sys
import os
import argparse
from typing import List, Optional

def print_help():
    """Print help information for the CLI tool."""
    print("""
Azure DevOps to GitHub Migration Tool - CLI

Usage:
  azuredevops-github-migration <command> [options]

Commands:
    init        Initialize configuration files
    migrate     Migrate a single repository or use listing utilities
    analyze     Analyze Azure DevOps organization  
    batch       Batch migrate multiple repositories
    doctor      Run environment & configuration diagnostics
    update-env  Run Test-MigrationEnv.ps1 to load/update .env variables
    interactive Launch arrow-key interactive menu (requires questionary)
    help        Show this help message
    version     Show version information

Examples:
  # Initialize configuration
  azuredevops-github-migration init --template jira-users
  
    # List projects / repos (note: list flags belong to 'migrate' subcommand)
    azuredevops-github-migration migrate --list-projects
    azuredevops-github-migration migrate --list-repos "MyProject"

    # Migrate single repository
    azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json
  
    # Analyze organization (default config.json assumed)
    azuredevops-github-migration analyze --create-plan

    # Quick discovery (analyze mode)
    azuredevops-github-migration analyze --list-projects
        azuredevops-github-migration analyze --list-repos "MyProject"

    # Verbose debug (echo sanitized config)
    azuredevops-github-migration analyze --debug --list-projects

        # One-shot quickstart (init + doctor + analyze projects) (new)
        azuredevops-github-migration quickstart --template jira-users
  
  # Batch migration
  azuredevops-github-migration batch --plan migration_plan.json --config config.json

For detailed help on a specific command:
  azuredevops-github-migration <command> --help

Documentation: https://github.com/stewartburton/azuredevops-github-migration/blob/main/docs/user-guide/HOW_TO_GUIDE.md
""")

def main(args: Optional[List[str]] = None):
    """Main CLI entry point."""
    if args is None:
        args = sys.argv[1:]
    
    if not args or args[0] in ['-h', '--help', 'help']:
        print_help()
        return 0
        
    if args[0] in ['-v', '--version', 'version']:
        from . import __version__
        print(f"Azure DevOps to GitHub Migration Tool v{__version__}")
        return 0
    
    # Global flag passthrough (collect before subcommand dispatch)
    global_debug = False
    if '--debug' in args:
        global_debug = True
        args = [a for a in args if a != '--debug']
        # Set env var so subcommands can detect even if they don't expose their own flag
        os.environ.setdefault('MIGRATION_DEBUG', '1')

    command = args[0]
    
    try:
        if command == 'init':
            from .init import main as init_main
            return init_main(args[1:])
        elif command == 'migrate':
            from .migrate import main as migrate_main
            # If user used only global --debug and didn't pass migrate's own flag, append it
            if global_debug and '--debug' not in args:
                return migrate_main(['--debug'] + args[1:])
            return migrate_main(args[1:])
        elif command == 'analyze':
            from .analyze import main as analyze_main  
            if global_debug and '--debug' not in args:
                return analyze_main(['--debug'] + args[1:])
            return analyze_main(args[1:])
        elif command == 'batch':
            from .batch_migrate import main as batch_main
            return batch_main(args[1:])
        elif command == 'doctor':
            from .doctor import main as doctor_main
            return doctor_main(args[1:])
        elif command == 'quickstart':
            try:
                from .quickstart import main as quick_main
            except ImportError:
                print("Quickstart module not found (developer mode only).")
                return 1
            # propagate debug
            if global_debug and '--debug' not in args:
                return quick_main(['--debug'] + args[1:])
            return quick_main(args[1:])
        elif command == 'update-env':
            from .interactive import run_update_env
            return run_update_env()
        elif command == 'interactive':
            from .interactive import interactive_menu
            return interactive_menu()
        else:
            print(f"Unknown command: {command}")
            print("Run 'azuredevops-github-migration help' for usage information")
            return 1
            
    except ImportError as e:
        print(f"Error importing command module: {e}")
        return 1
    except Exception as e:
        print(f"Error executing command: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())