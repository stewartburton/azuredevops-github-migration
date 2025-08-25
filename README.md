# Azure DevOps to GitHub Migration Tool

A comprehensive Python tool for migrating repositories, work items, and other artifacts from Azure DevOps to GitHub.

## Features

- **Repository Migration**: Clone and migrate Git repositories from Azure DevOps to GitHub with complete history
- **Pipeline Conversion**: Convert Azure DevOps pipelines to GitHub Actions workflows
- **Work Items to Issues** (Optional): Convert Azure DevOps work items to GitHub issues - skip if using Jira/other issue tracking
- **Batch Processing**: Migrate multiple repositories using a migration plan
- **Organization Analysis**: Analyze Azure DevOps organizations to plan migrations
- **Comprehensive Logging**: Detailed logs and migration reports
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Retry Logic**: Automatic retry on transient failures

## 📁 Project Structure

```
azuredevops-github-migration/
├── README.md                    # Project overview (you are here)
├── requirements.txt             # Python dependencies  
├── setup.py                     # Package installation
│
├── src/                        # 🐍 Source Code
│   ├── migrate.py              # Main migration tool
│   ├── analyze.py              # Organization analysis  
│   ├── batch_migrate.py        # Batch operations
│   └── utils.py                # Shared utilities
│
├── config/                     # ⚙️ Configuration Templates
│   └── config.template.json    # Main configuration template
│
├── examples/                   # 📋 Ready-to-Use Examples
│   ├── jira-users-config.json  # For Jira users (most common)
│   ├── full-migration-config.json  # Complete migration
│   └── sample-migration-plan.json  # Batch migration plan
│
├── scripts/                    # 🔧 Setup & Utilities  
│   └── setup.sh               # Automated installation
│
├── tests/                      # 🧪 Test Suite
│   ├── test_migrate_basic.py   # Essential tests
│   └── test_migrate.py         # Comprehensive tests
│
└── docs/                       # 📚 Documentation
    ├── user-guide/             # User Documentation
    │   ├── HOW_TO_GUIDE.md     # Step-by-step instructions
    │   ├── PRE_MIGRATION_CHECKLIST.md  # 100+ item checklist
    │   └── TESTING.md          # Testing procedures
    └── technical/              # Technical Documentation  
        ├── api.md              # API reference
        ├── configuration.md    # Configuration guide
        └── troubleshooting.md  # Problem resolution
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Choose your configuration template
cp examples/jira-users-config.json config.json          # For Jira users
# OR
cp config/config.template.json config.json              # Custom configuration

# Set up environment variables
cp .env.example .env
# Edit .env with your tokens: AZURE_DEVOPS_PAT and GITHUB_TOKEN
```

### Basic Migration Commands

```bash
# 1. Validate your setup
python src/migrate.py --validate-only --config config.json

# 2. Analyze your organization (optional)
python src/analyze.py --create-plan --config config.json

# 3. Test migration (safe, no changes)
python src/migrate.py --project "MyProject" --repo "my-repo" --dry-run --config config.json

# 4. Actual migration (Jira users - most common)
python src/migrate.py --project "MyProject" --repo "my-repo" --no-issues --config config.json

# 5. Batch migration
python src/batch_migrate.py --plan examples/sample-migration-plan.json --config config.json
```

## Configuration

### Environment Variables

Create a `.env` file with your authentication tokens:

```bash
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

### Migration Config

Edit `migration_config.yaml` to configure:

- Azure DevOps organization and authentication
- GitHub organization and settings  
- Work item type mappings
- State mappings
- Rate limiting settings
- Logging configuration

## Scripts Overview

### `migrate.py` - Main Migration Script

Single repository migration with full control over the process.

```bash
# Basic usage
python migrate.py --project "MyProject" --repo "my-repo"

# Custom GitHub repo name
python migrate.py --project "MyProject" --repo "my-repo" --github-repo "new-name"

# Skip work item migration
python migrate.py --project "MyProject" --repo "my-repo" --no-issues
```

### `analyze.py` - Organization Analyzer

Analyze your Azure DevOps organization to understand what needs to be migrated.

```bash
# Analyze entire organization
python analyze.py

# Analyze specific project
python analyze.py --project "MyProject"

# Create migration plan
python analyze.py --create-plan

# Export as CSV
python analyze.py --format csv
```

### `batch_migrate.py` - Batch Migration

Migrate multiple repositories using a migration plan.

```bash
# Create sample migration plan
python batch_migrate.py --create-sample

# Dry run to see what would be migrated
python batch_migrate.py --dry-run

# Execute batch migration
python batch_migrate.py --plan migration_plan.json
```

### `utils.py` - Utility Functions

Contains helper functions for:
- HTML to Markdown conversion
- Work item formatting
- Rate limiting
- Progress tracking
- Configuration validation

## Migration Process

### What Gets Migrated

✅ **Repository Structure** (Always)
- Complete Git history with all commits
- All branches and tags
- Repository metadata (name, description)

✅ **Azure DevOps Pipelines** (Always)
- Converted to GitHub Actions workflows
- Basic pipeline structure and steps
- Build and deployment configurations

✅ **Work Items → Issues** (Optional - Skip if using Jira)
- Title and description (HTML → Markdown)
- Work item type → Labels
- State information
- Priority and other metadata
- Acceptance criteria (if present)
- Reproduction steps (for bugs)

> **Note for Jira Users:** Use `--no-issues` flag to skip work item migration since you're managing issues in Jira.

### What Doesn't Get Migrated

❌ **Git-level items that require special handling:**
- Pull requests (GitHub API doesn't support creating historical PRs)
- Branch policies
- Build pipelines

❌ **Azure DevOps specific features:**
- Wiki pages
- Test plans and cases
- Boards configuration
- Extensions and customizations

## 📚 Documentation Quick Links

### 👥 **For End Users**
- **[📖 How-To Guide](docs/user-guide/HOW_TO_GUIDE.md)** - Complete step-by-step migration instructions
- **[✅ Pre-Migration Checklist](docs/user-guide/PRE_MIGRATION_CHECKLIST.md)** - 100+ validation items before migration  
- **[🧪 Testing Guide](docs/user-guide/TESTING.md)** - Comprehensive testing procedures

### 🔧 **For Technical Teams**
- **[⚙️ Configuration Reference](docs/technical/configuration.md)** - Complete configuration options
- **[🔍 Troubleshooting Guide](docs/technical/troubleshooting.md)** - Problem resolution and debugging
- **[🔌 API Documentation](docs/technical/api.md)** - Technical API reference

### 📋 **Ready-to-Use Examples**
- **[examples/jira-users-config.json](examples/jira-users-config.json)** - Optimized for Jira users (most common)
- **[examples/full-migration-config.json](examples/full-migration-config.json)** - Complete migration with work items
- **[examples/sample-migration-plan.json](examples/sample-migration-plan.json)** - Batch migration template

## Authentication

### Azure DevOps Personal Access Token

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Create new token with these scopes:
   - **Code**: Read
   - **Work Items**: Read
   - **Project and Team**: Read

### GitHub Personal Access Token

1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
2. Create token with these scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories)
   - `admin:org` (if migrating to organization)

## Migration Planning

### 1. Analysis Phase

```bash
python analyze.py --create-plan
```

This generates:
- `analysis_report_[org]_[timestamp].json` - Detailed analysis
- `migration_plan_[org]_[timestamp].json` - Recommended migration plan

### 2. Plan Review

Edit the migration plan to:
- Customize repository names
- Set migration priorities
- Configure issue migration preferences
- Add descriptions and notes

### 3. Execution

```bash
# Test with dry run first
python batch_migrate.py --dry-run --plan your_plan.json

# Execute migration
python batch_migrate.py --plan your_plan.json
```

## Logging and Reports

### Migration Logs
- Console output with progress indicators
- Detailed log file: `migration.log`
- Configurable log levels

### Migration Reports
- JSON reports with complete migration data
- Statistics and success/failure tracking
- Timestamp-based file naming

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify your personal access tokens
- Check token permissions/scopes
- Ensure tokens haven't expired

**Rate Limiting**
- Tool includes built-in rate limiting
- Adjust `delay_between_requests` in config if needed
- GitHub has stricter limits for organization repositories

**Large Repositories**
- Tool handles large repos, but migration time increases
- Consider migrating during off-peak hours
- Monitor disk space for local clones

**Work Item Conversion**
- Complex HTML in work items may need manual review
- Custom fields won't be migrated automatically
- Large work item descriptions may be truncated

### Getting Help

1. Check the migration logs for detailed error messages
2. Verify your configuration settings
3. Test with a small repository first
4. Review GitHub and Azure DevOps API documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Limitations and Considerations

- **Repository Size**: Very large repositories (>5GB) may take significant time
- **API Limits**: Both Azure DevOps and GitHub have API rate limits
- **Historical Data**: Some metadata may be lost in translation
- **Custom Fields**: Azure DevOps custom fields require manual mapping
- **Attachments**: Work item attachments are not migrated automatically

## Security Notes

- Never commit your personal access tokens
- Use environment variables for sensitive configuration
- Review migration reports before sharing
- Consider using service accounts for production migrations