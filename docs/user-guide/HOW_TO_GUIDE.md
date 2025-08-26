# How to Use the Azure DevOps to GitHub Migration Tool

> **TL;DR (Jira Mode – code & pipelines only, no work items)**
> ```bash
> # 1. Use Jira-focused config (disables work items)
> cp examples/jira-users-config.json config.json
>
> # 2. Analyze (skips & omits work items; creates plan)
> python src/analyze.py --project "MyProject" --create-plan --config config.json --skip-work-items
>
> # 3. Dry run a single repo
> python src/migrate.py --project "MyProject" --repo "my-repo" --dry-run --config config.json
>
> # 4. Migrate the repo (issues auto-disabled)
> python src/migrate.py --project "MyProject" --repo "my-repo" --config config.json
>
> # 5. Batch migrate (plan has no migrate_issues fields)
> python src/batch_migrate.py --plan migration_plan_<org>_*.json --config config.json
> ```
> `--skip-work-items` = no WIQL calls + no work item fields + later migrations treat repos as code-only.

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
9. [Key CLI Flags](#key-cli-flags-quick-reference)
10. [Advanced Configuration](#advanced-configuration)
11. [Validation and Testing](#validation-and-testing)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)
14. [Example End-to-End Workflow](#example-end-to-end-workflow)

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
# Clone the repository
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Set up configuration templates
- Create necessary directories

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

Use least privilege. Start with the minimum scopes and add only if the tool reports an authorization error for a feature you actually need.

### Required Personal Access Token (PAT) Scopes

#### Azure DevOps PAT
**Minimum** (repository migration only – no work items):
- Code: Read (clone repositories, enumerate branches/tags)
- Project and Team: Read (list projects & repos)

**Add ONLY if needed:**
- Work Items: Read (when converting work items to GitHub issues; omit when using `--no-issues` or Jira)
- Code: Read & Write (only if you intentionally push changes back to Azure DevOps – not required for one‑way migration)

#### GitHub PAT
**Minimum** (target repos already exist or created manually):
- repo (covers contents, issues, pulls for private & public repos)

**Add ONLY if needed:**
- admin:org (tool needs to create new repositories inside an organization)
- delete_repo (you implement rollback that deletes created repos)
- workflow (you programmatically manipulate Actions runs beyond committing YAML files)

### Obtaining Tokens

#### Azure DevOps (Create PAT)
1. In any Azure DevOps page, click your avatar (top-right) → **User settings** → **Personal access tokens**.
2. Click **+ New Token**.
3. Fill in:
    - **Name**: e.g. `ado-migration-temp`.
    - **Organization**: (choose the source org).
    - **Expiration**: Short as practical (e.g. 30 or 60 days).
4. Under **Scopes**, click **Custom defined** and select ONLY the scopes you need:
    - Start with: Code (Read), Project and Team (Read).
    - Add Work Items (Read) ONLY if migrating issues.
5. Click **Create** and copy the token immediately (cannot be recovered later).

#### GitHub (Fine‑grained PAT – Recommended)
1. GitHub → **Settings** (profile) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Token name**: e.g. `gh-migration-fg`.
3. **Expiration**: Select a short duration matching migration window.
4. **Resource owner**: Select the user or organization that owns the destination repositories.
5. **Repository access**: Choose specific repositories (preferred) or **All repositories** only if necessary.
6. **Permissions**: Under *Repository permissions* grant:
    - **Contents**: Read and write (required for pushing migrated history).
    - **Metadata**: Read (automatically included).
    - **Issues**: Read & write (only if migrating work items → GitHub issues).
7. Generate token and copy it once. Store securely.

#### GitHub (Classic PAT – When Fine‑grained Not Suitable)
1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token**.
2. **Note**: Provide a descriptive name, set a short expiration.
3. Select scopes:
    - **repo** (includes repo:status, repo_deployment, public_repo, repo:invite).
    - **admin:org** ONLY if the tool itself will create repositories in the organization.
    - **delete_repo** ONLY if you will automate rollback deletion.
4. Generate & copy once. Store securely.

## Planning Your Migration

### Step 1: Analyze Your Organization

Before migrating, analyze what you have:

```bash
# Validate your setup first
python src/migrate.py --validate-only --config config.json

# Analyze entire organization
python src/analyze.py --create-plan --config config.json

# Analyze specific project
python src/analyze.py --project "MyProject" --create-plan --config config.json

# Jira mode (omit & skip work items)
python src/analyze.py --project "MyProject" --create-plan --config config.json --skip-work-items

# Export as CSV
python src/analyze.py --format csv --config config.json
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
# Basic migration commands

# 1. Test migration (safe, no changes)
python src/migrate.py --project "MyProject" --repo "my-repo" --dry-run --config config.json

# 2. Typical migration for Jira users (repository + pipelines only)
python src/migrate.py --project "MyProject" --repo "my-repo" --no-issues --config config.json

# 3. With custom GitHub repository name
python src/migrate.py --project "MyProject" --repo "my-repo" --github-repo "new-repo-name" --config config.json

# 4. Repository-only pipelines (instead of all project pipelines)
python src/migrate.py --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# 5. Exclude disabled pipelines & verify remote branches post-push
python src/migrate.py --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --verify-remote --config config.json

# 6. Full migration including work items (if not using Jira)
python src/migrate.py --project "MyProject" --repo "my-repo" --config config.json
```

### Batch Migration

```bash
# Create sample migration plan
python src/batch_migrate.py --create-sample

# Test with dry run first (uses default plan name)
python src/batch_migrate.py --dry-run --config config.json

# Execute batch migration with explicit plan
python src/batch_migrate.py --plan migration_plan.json --config config.json
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

### 2. Verify Remote Branches (if using --verify-remote)

Check the migration logs for:
- Remote vs local branch comparison
- Any missing or extra branches reported
- Confirmation that all branches were pushed successfully

### 3. Verify Work Items → Issues Migration (if enabled)

In GitHub, check:
- Issues were created with correct titles
- Descriptions were converted from HTML to Markdown
- Labels were applied correctly
- Issue states match your configuration

### 4. Update Team Workflows

- Update CI/CD pipelines to point to GitHub
- Update documentation links
- Notify team members of the new repository location
- Update any integrations or webhooks

### 5. Archive Azure DevOps Repositories

Once you've verified the migration:
1. Make repositories read-only in Azure DevOps
2. Add a README pointing to the new GitHub location
3. Consider archiving after a transition period

## Common Scenarios

### Scenario 1: Organizations Using Jira (Most Common)

If you're using Jira for issue tracking and only need to migrate Git repositories and pipelines:

```bash
# Use the Jira-focused example config (sets migrate_work_items=false)
cp examples/jira-users-config.json config.json

# Analyze without querying work item data
python src/analyze.py --project "MyProject" --create-plan --config config.json --skip-work-items

# Dry run a repo (issue migration auto-disabled; no need for --no-issues)
python src/migrate.py --project "MyProject" --repo "my-repo" --dry-run --config config.json

# Actual migration (issues suppressed automatically)
python src/migrate.py --project "MyProject" --repo "my-repo" --config config.json

# Batch dry run (plan produced by --skip-work-items omits migrate_issues fields)
python src/batch_migrate.py --plan migration_plan_<org>_*.json --dry-run --config config.json

# Batch execute
python src/batch_migrate.py --plan migration_plan_<org>_*.json --config config.json
```

**What you get:**
- ✅ Complete Git history migration
- ✅ Azure DevOps pipelines converted to GitHub Actions
- ✅ All branches and tags preserved
- ❌ No GitHub issues created (continue using Jira)

### Scenario 2: Advanced Pipeline Control

```bash
# Repository-specific pipelines only (not all project pipelines)
python src/migrate.py --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# Exclude disabled/paused pipelines
python src/migrate.py --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --config config.json

# Combine multiple flags for precision
python src/migrate.py --project "MyProject" --repo "my-repo" \
    --pipelines-scope repository --exclude-disabled-pipelines --verify-remote --dry-run --config config.json
```

### Scenario 3: Large Organization Migration

```bash
# 1. Start with analysis
python src/analyze.py --create-plan --config config.json

# 2. Edit the generated plan to prioritize critical repositories
# 3. Run migration in batches
python src/batch_migrate.py --plan high_priority_repos.json --config config.json
python src/batch_migrate.py --plan medium_priority_repos.json --config config.json
```

### Scenario 4: Selective Repository Migration

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

python src/batch_migrate.py --plan custom_plan.json --config config.json
```

### Scenario 5: Work Items Only Migration

If you only want to migrate work items to issues (no Git repositories):

```bash
# Configure for work items only
python src/migrate.py --project "MyProject" --repo "my-repo" --no-git --no-pipelines --config config.json
```

Or in your config.json:
```json
{
  "migration": {
    "migrate_work_items": true,
    "migrate_git_history": false,
    "migrate_pipelines": false
  }
}
```

### Scenario 6: Different GitHub Organization

```json
{
  "github": {
    "organization": "new-company-org",
    "create_private_repos": false
  }
}
```

## Key CLI Flags (Quick Reference)

| Flag | Purpose | Default |
|------|---------|--------|
| `--dry-run` | Simulate migration without side effects | off |
| `--no-issues` | Skip work item → issue conversion | off |
| `--no-pipelines` | Skip pipeline conversion | off |
| `--pipelines-scope {project\|repository}` | Control pipeline selection scope | project |
| `--exclude-disabled-pipelines` | Omit disabled/paused pipelines | off |
| `--no-git` | Skip Git history migration | off |
| `--verify-remote` | Compare remote branch list to local after push | off |
| `--skip-work-items` (analyze) | Do not query work items; omit related fields & auto-disable issue migration later | off |
| `--debug` | Verbose logging | off |
| `--validate-only` | Validate config & credentials only | off |

**Automatic behaviors:**
* If config contains `"migrate_work_items": false`, single repo migrations suppress issues without needing `--no-issues`.
* If a migration plan omits `migrate_issues` (produced via `--skip-work-items`), batch migration treats all entries as code-only.
* Use `--no-issues` for explicitness when communicating commands to others.

## Advanced Configuration

### Ready-to-Use Configuration Examples

The tool provides several pre-configured templates in the `examples/` directory:

- **`examples/jira-users-config.json`** - Most common: Code & pipelines only (work items disabled)
- **`examples/full-migration-config.json`** - Complete migration including work items
- **`config/config.template.json`** - Blank template for custom configuration

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
# Validate your setup
python src/migrate.py --validate-only --config config.json

# Test with dry run
python src/migrate.py --project "MyProject" --repo "test-repo" --dry-run --config config.json

# Verify tokens work by running analysis
python src/analyze.py --project "MyProject" --config config.json
```

### Post-Migration Validation

```bash
# Compare repository statistics
python src/analyze.py --project "MyProject" --config config.json > before_migration.txt
# After migration, check GitHub repository for equivalent data

# Verify migration reports
ls -la migration_report_*.json
ls -la analysis_report_*.json
```

## Best Practices

1. **Start Small**: Begin with a test repository to validate the process
2. **Plan Thoroughly**: Use the analysis tool to understand your data
3. **Test Connections**: Verify API access before large migrations
4. **Monitor Rate Limits**: Large organizations may hit API limits
5. **Backup Data**: Ensure you have backups before beginning
6. **Communicate Changes**: Inform your team about new repository locations
7. **Gradual Transition**: Migrate in phases rather than all at once

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

If you encounter issues:

1. Check the migration logs (`migration.log`)
2. Review the troubleshooting documentation (`docs/technical/troubleshooting.md`)
3. Validate your configuration against the template
4. Test with a smaller dataset first
5. Review GitHub and Azure DevOps API documentation

## Example End-to-End Workflow

Here's a complete example workflow:

```bash
# 1. Setup
./scripts/setup.sh

# 2. Configure
cp examples/jira-users-config.json config.json  # For Jira users (most common)
# Edit config.json and .env files

# 3. Validate
python src/migrate.py --validate-only --config config.json

# 4. Analyze
python src/analyze.py --create-plan --config config.json
# For Jira users: add --skip-work-items flag

# 5. Plan
# Edit the generated migration plan

# 6. Test
python src/batch_migrate.py --dry-run --plan migration_plan.json --config config.json

# 7. Execute
python src/batch_migrate.py --plan migration_plan.json --config config.json

# 8. Verify
# Check GitHub repositories and issues (if enabled)
# Review migration logs for any branch verification results
```

This completes the migration process. Your Azure DevOps repositories and work items should now be successfully migrated to GitHub!

---

## Additional Resources

- **[📖 Complete README](../../README.md)** - Full project documentation with all features
- **[✅ Pre-Migration Checklist](PRE_MIGRATION_CHECKLIST.md)** - 100+ validation items before migration  
- **[🧪 Testing Guide](TESTING.md)** - Comprehensive testing procedures
- **[⚙️ Configuration Reference](../technical/configuration.md)** - Complete configuration options
- **[🔍 Troubleshooting Guide](../technical/troubleshooting.md)** - Problem resolution and debugging
- **[🔌 API Documentation](../technical/api.md)** - Technical API reference