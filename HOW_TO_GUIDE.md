# How to Use the Azure DevOps to GitHub Migration Tool

This comprehensive guide will walk you through the entire process of migrating your repositories and work items from Azure DevOps to GitHub.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Authentication Setup](#authentication-setup)
5. [Planning Your Migration](#planning-your-migration)
6. [Running Migrations](#running-migrations)
7. [Post-Migration Steps](#post-migration-steps)
8. [Common Scenarios](#common-scenarios)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- **Python 3.7+** installed on your system
- **Git** installed and configured
- **Administrative access** to your Azure DevOps organization
- **Owner/Admin permissions** on your GitHub organization (if applicable)
- **Sufficient disk space** for repository clones during migration

## Installation

### Option 1: Automated Setup (Recommended)

```bash
# Clone or download the migration tool
git clone <repository-url>
cd azuredevops-github-migration

# Run the setup script
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Set up configuration templates
- Create necessary directories

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy configuration templates
cp config.template.json config.json
cp .env.example .env
```

## Configuration

### 1. Edit Configuration File

Open `config.json` and update the following sections:

```json
{
  "azure_devops": {
    "organization": "your-org-name",
    "personal_access_token": "${AZURE_DEVOPS_PAT}",
    "project": "your-project-name"
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "organization": "your-github-org",
    "create_private_repos": true
  }
}
```

### 2. Environment Variables

Edit `.env` file with your credentials:

```bash
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

**Important**: Never commit these files with real tokens!

## Authentication Setup

### Azure DevOps Personal Access Token

1. Go to Azure DevOps → Click your profile → Personal Access Tokens
2. Click "New Token"
3. Set the following scopes:
   - **Code**: Read & Write (for repositories)
   - **Work Items**: Read (for work items)
   - **Project and Team**: Read (for project information)
4. Copy the generated token to your `.env` file

### GitHub Personal Access Token

1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
2. Click "Generate new token"
3. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `admin:org` (if migrating to an organization)
   - `user` (for user information)
4. Copy the generated token to your `.env` file

## Planning Your Migration

### Step 1: Analyze Your Organization

Before migrating, analyze what you have:

```bash
# Analyze entire organization
python analyze.py

# Analyze specific project
python analyze.py --project "MyProject"

# Generate migration plan
python analyze.py --create-plan
```

This creates:
- `analysis_report_[org]_[timestamp].json` - Complete analysis
- `migration_plan_[org]_[timestamp].json` - Suggested migration plan

### Step 2: Review the Migration Plan

Edit the generated migration plan to:
- Customize repository names
- Set migration priorities
- Configure which work items to migrate
- Add descriptions and notes

Example migration plan:
```json
[
  {
    "project_name": "MyProject",
    "repo_name": "legacy-app",
    "github_repo_name": "new-modern-app",
    "migrate_issues": true,
    "priority": "high",
    "description": "Main application repository"
  }
]
```

## Running Migrations

### Single Repository Migration

```bash
# Basic migration
python migrate.py --project "MyProject" --repo "my-repo"

# With custom GitHub repository name
python migrate.py --project "MyProject" --repo "my-repo" --github-repo "new-repo-name"

# Skip work item migration
python migrate.py --project "MyProject" --repo "my-repo" --no-issues
```

### Batch Migration

```bash
# Test with dry run first
python batch_migrate.py --dry-run --plan migration_plan.json

# Execute the migration
python batch_migrate.py --plan migration_plan.json
```

### Monitor Progress

The tool provides:
- **Console output** with progress indicators
- **Detailed logs** in `migration.log`
- **Migration reports** in JSON format

## Post-Migration Steps

### 1. Verify Repository Migration

Check that:
- All branches were migrated
- Commit history is intact
- Repository settings are correct

```bash
# Clone the migrated repository
git clone https://github.com/your-org/migrated-repo.git
cd migrated-repo

# Verify branches
git branch -a

# Check commit history
git log --oneline -10
```

### 2. Verify Work Items → Issues Migration

In GitHub, check:
- Issues were created with correct titles
- Descriptions were converted from HTML to Markdown
- Labels were applied correctly
- Issue states match your configuration

### 3. Update Team Workflows

- Update CI/CD pipelines to point to GitHub
- Update documentation links
- Notify team members of the new repository location
- Update any integrations or webhooks

### 4. Archive Azure DevOps Repositories

Once you've verified the migration:
1. Make repositories read-only in Azure DevOps
2. Add a README pointing to the new GitHub location
3. Consider archiving after a transition period

## Common Scenarios

### Scenario 1: Large Organization Migration

```bash
# 1. Start with analysis
python analyze.py --create-plan

# 2. Edit the generated plan to prioritize critical repositories
# 3. Run migration in batches
python batch_migrate.py --plan high_priority_repos.json
python batch_migrate.py --plan medium_priority_repos.json
```

### Scenario 2: Selective Repository Migration

```bash
# Create custom migration plan
cat > custom_plan.json << 'EOF'
[
  {
    "project_name": "MyProject",
    "repo_name": "critical-app",
    "github_repo_name": "critical-app",
    "migrate_issues": true
  },
  {
    "project_name": "MyProject", 
    "repo_name": "legacy-tool",
    "github_repo_name": "archived-legacy-tool",
    "migrate_issues": false
  }
]
EOF

python batch_migrate.py --plan custom_plan.json
```

### Scenario 3: Work Items Only Migration

If you only want to migrate work items to issues:

```json
{
  "migration": {
    "migrate_work_items": true,
    "migrate_pull_requests": false
  }
}
```

### Scenario 4: Different GitHub Organization

```json
{
  "github": {
    "organization": "new-company-org",
    "create_private_repos": false
  }
}
```

## Advanced Configuration

### Custom Field Mappings

Map Azure DevOps custom fields to GitHub labels:

```json
{
  "work_item_mapping": {
    "type_mappings": {
      "User Story": "enhancement",
      "Bug": "bug",
      "Custom Work Item": "custom-type"
    },
    "priority_mappings": {
      "1": "priority-critical",
      "2": "priority-high",
      "3": "priority-medium",
      "4": "priority-low"
    }
  }
}
```

### Rate Limiting Configuration

Adjust API call rates:

```json
{
  "rate_limiting": {
    "azure_devops_requests_per_second": 10,
    "github_requests_per_second": 30,
    "enable_backoff": true
  }
}
```

### Filtering Options

Exclude specific repositories or work items:

```json
{
  "filters": {
    "exclude_repositories": ["temp-repo", "test-repo"],
    "exclude_work_item_types": ["Test Case", "Shared Steps"],
    "date_range": {
      "start_date": "2023-01-01",
      "end_date": "2023-12-31"
    }
  }
}
```

## Validation and Testing

### Pre-Migration Testing

```bash
# Test connection to Azure DevOps
python -c "from migrate import AzureDevOpsClient; client = AzureDevOpsClient('org', 'token'); print(len(client.get_projects()))"

# Test connection to GitHub
python -c "from migrate import GitHubClient; client = GitHubClient('token'); print(client.get_user()['login'])"
```

### Post-Migration Validation

```bash
# Compare repository statistics
python analyze.py --project "MyProject" > before_migration.txt
# After migration, check GitHub repository for equivalent data
```

## Best Practices

1. **Start Small**: Begin with a test repository to validate the process
2. **Plan Thoroughly**: Use the analysis tool to understand your data
3. **Test Connections**: Verify API access before large migrations
4. **Monitor Rate Limits**: Large organizations may hit API limits
5. **Backup Data**: Ensure you have backups before beginning
6. **Communicate Changes**: Inform your team about new repository locations
7. **Gradual Transition**: Migrate in phases rather than all at once

## Getting Help

If you encounter issues:

1. Check the migration logs (`migration.log`)
2. Review the troubleshooting documentation (`docs/troubleshooting.md`)
3. Validate your configuration against the template
4. Test with a smaller dataset first

## Example End-to-End Workflow

Here's a complete example workflow:

```bash
# 1. Setup
./setup.sh

# 2. Configure
# Edit config.json and .env files

# 3. Analyze
python analyze.py --create-plan

# 4. Plan
# Edit the generated migration plan

# 5. Test
python batch_migrate.py --dry-run --plan migration_plan.json

# 6. Execute
python batch_migrate.py --plan migration_plan.json

# 7. Verify
# Check GitHub repositories and issues
```

This completes the migration process. Your Azure DevOps repositories and work items should now be successfully migrated to GitHub!