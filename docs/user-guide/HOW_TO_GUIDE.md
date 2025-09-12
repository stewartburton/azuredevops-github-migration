# How to Use the Azure DevOps to GitHub Migration Tool

> **TL;DR (Jira Mode – code & pipelines only, no work items)**
> ```bash
> # 1. Use Jira-focused config (disables work items)
> cp examples/jira-users-config.json config.json
>
> # 2. Analyze (skips & omits work items; creates plan)
> azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items
>
> # 3. Dry run a single repo
> azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json
>
> # 4. Migrate the repo (issues auto-disabled)
> azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json
>
> # 5. Batch migrate (plan has no migrate_issues fields)
> azuredevops-github-migration batch --plan migration_plan_<org>_*.json --config config.json
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
15. [Configuring Azure DevOps Pipelines for GitHub](#configuring-azure-devops-pipelines-for-github)

## Prerequisites

Before you begin, ensure you have:

- **Python 3.7+** installed on your system
- **Git** installed and configured
- **Administrative access** to your Azure DevOps organization
- **Owner/Admin permissions** on your GitHub organization (if applicable)
- **Sufficient disk space** for repository clones during migration

## Installation

### Option 1: PyPI Installation (Recommended)

```bash
# Install from PyPI
pip install azuredevops-github-migration

# Verify installation
azuredevops-github-migration --version

# Initialize configuration (creates config.json and .env template)
azuredevops-github-migration init --template jira-users    # For Jira users (most common)
# OR
azuredevops-github-migration init --template full          # Complete migration setup

# Edit the created config.json and .env files with your settings

### (New) Optional Interactive Menu & Environment Loader

After installation you can use two convenience commands to simplify onboarding:

| Command | Purpose | Notes |
|---------|---------|-------|
| `azuredevops-github-migration interactive` | Arrow-key menu for common actions (init, analyze, migrate, batch, doctor, env update) | Requires optional dependency `questionary` (`pip install questionary`) |
| `azuredevops-github-migration update-env` | Invokes PowerShell helper to load & audit environment variables from `.env` | Requires `pwsh` or `powershell` in PATH |

Benefits:
* Eliminates need to remember commands immediately
* Ensures environment variables are loaded before running analysis/migration
* Provides a quick, masked audit of token presence

If PowerShell is not installed the `update-env` command will print guidance and exit; the rest of the interactive menu continues to function (except that option).
```

### Option 2: Automated Setup from Source

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

### Option 3: Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration
pip install -e .

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

#### (New) Loading Environment Variables Automatically

Instead of manually exporting variables each session you can run:

```bash
azuredevops-github-migration update-env
```

This executes the bundled PowerShell script (`scripts/Test-MigrationEnv.ps1 -Load -Overwrite -Json`) which:
* Loads values from `.env` into the current process environment
* Outputs a masked JSON summary (consumed internally by the Python wrapper)
* Creates a stub `.env` if missing, prompting you to fill real values

Within the interactive menu you can select "Update / load .env" to perform the same action using arrow keys.

If you prefer a pure Python diagnostic, use:

```bash
azuredevops-github-migration doctor
```

The `doctor` command auto-loads `.env` (without overwriting existing shell values) to report token presence.

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
azuredevops-github-migration migrate --validate-only --config config.json

# Analyze entire organization (config.json default)
azuredevops-github-migration analyze --create-plan

# Analyze specific project
azuredevops-github-migration analyze --project "MyProject" --create-plan

# Jira mode (omit & skip work items)
azuredevops-github-migration analyze --project "MyProject" --create-plan --skip-work-items

# Export as CSV
azuredevops-github-migration analyze --format csv
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
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json

# 2. Typical migration for Jira users (repository + pipelines only)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-issues --config config.json

# 3. With custom GitHub repository name
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --github-repo "new-repo-name" --config config.json

# 4. Repository-only pipelines (instead of all project pipelines)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# 5. Exclude disabled pipelines & verify remote branches post-push
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --verify-remote --config config.json

# 6. Full migration including work items (if not using Jira)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json
```

### Batch Migration

```bash
# Create sample migration plan
azuredevops-github-migration batch --create-sample

# Test with dry run first (uses default plan name)
azuredevops-github-migration batch --dry-run --config config.json

# Execute batch migration with explicit plan
azuredevops-github-migration batch --plan migration_plan.json --config config.json
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

- **Update CI/CD pipelines to point to GitHub**: This is a critical step that requires detailed configuration. See the comprehensive [Configuring Azure DevOps Pipelines for GitHub](#configuring-azure-devops-pipelines-for-github) section below for step-by-step instructions on:
  - Creating GitHub service connections
  - Updating pipeline repository sources  
  - Configuring variable groups and environments
  - Testing and validating pipeline configurations
  - Bulk updating hundreds of pipelines safely
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
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items

# Dry run a repo (issue migration auto-disabled; no need for --no-issues)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json

# Actual migration (issues suppressed automatically)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json

# Batch dry run (plan produced by --skip-work-items omits migrate_issues fields)
azuredevops-github-migration batch --plan migration_plan_<org>_*.json --dry-run --config config.json

# Batch execute
azuredevops-github-migration batch --plan migration_plan_<org>_*.json --config config.json
```

**What you get:**
- ✅ Complete Git history migration
- ✅ Azure DevOps pipelines converted to GitHub Actions
- ✅ All branches and tags preserved
- ❌ No GitHub issues created (continue using Jira)

### Scenario 2: Advanced Pipeline Control

```bash
# Repository-specific pipelines only (not all project pipelines)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# Exclude disabled/paused pipelines
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --config config.json

# Combine multiple flags for precision
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" \
    --pipelines-scope repository --exclude-disabled-pipelines --verify-remote --dry-run --config config.json
```

### Scenario 3: Large Organization Migration

```bash
# 1. Start with analysis
azuredevops-github-migration analyze --create-plan

# 2. Edit the generated plan to prioritize critical repositories
# 3. Run migration in batches
azuredevops-github-migration batch --plan high_priority_repos.json --config config.json
azuredevops-github-migration batch --plan medium_priority_repos.json --config config.json
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

azuredevops-github-migration batch --plan custom_plan.json --config config.json
```

### Scenario 5: Work Items Only Migration

If you only want to migrate work items to issues (no Git repositories):

```bash
# Configure for work items only
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-git --no-pipelines --config config.json
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
azuredevops-github-migration migrate --validate-only --config config.json

# Test with dry run
azuredevops-github-migration migrate --project "MyProject" --repo "test-repo" --dry-run --config config.json

# Verify tokens work by running analysis
azuredevops-github-migration analyze --project "MyProject" --config config.json
```

### Post-Migration Validation

```bash
# Compare repository statistics
azuredevops-github-migration analyze --project "MyProject" --config config.json > before_migration.txt
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
azuredevops-github-migration migrate --validate-only --config config.json

# 4. Analyze
azuredevops-github-migration analyze --create-plan
# For Jira users: add --skip-work-items flag

# 5. Plan
# Edit the generated migration plan

# 6. Test
azuredevops-github-migration batch --dry-run --plan migration_plan.json --config config.json

# 7. Execute
azuredevops-github-migration batch --plan migration_plan.json --config config.json

# 8. Verify
# Check GitHub repositories and issues (if enabled)
# Review migration logs for any branch verification results
```

This completes the migration process. Your Azure DevOps repositories and work items should now be successfully migrated to GitHub!

---

## Configuring Azure DevOps Pipelines for GitHub

After migrating your repositories from Azure DevOps to GitHub, you need to reconfigure your Azure DevOps pipelines to point to the new GitHub repository locations. This section provides comprehensive, step-by-step instructions for updating build pipelines, build & release pipelines, libraries, environments, and variables.

### Overview

Azure DevOps pipelines can continue to run against GitHub repositories with proper configuration. The key components that need updating are:

- **Pipeline repository sources** - Point to GitHub instead of Azure Repos
- **Service connections** - Authenticate with GitHub
- **Variable groups** - Update any repository-specific variables
- **Pipeline libraries** - Ensure proper access to shared resources
- **Environments** - Verify deployment target configurations
- **Branch policies** - Update if referencing specific repository paths

### Prerequisites

Before configuring pipelines, ensure you have:

- **Administrative access** to your Azure DevOps organization
- **Project Administrator** permissions for relevant projects
- **GitHub repository access** with appropriate permissions
- **Service Connection Administrator** role (if creating new connections)
- **Completed repository migration** to GitHub
- **GitHub Personal Access Token** with appropriate scopes

### Step 1: Create GitHub Service Connection

Each project needs a service connection to GitHub for pipeline authentication.

#### 1.1 Navigate to Service Connections

1. Go to your Azure DevOps organization: `https://dev.azure.com/{your-organization}`
2. Select the project containing your pipelines
3. Navigate to **Project Settings** (bottom-left gear icon)
4. Under **Pipelines**, select **Service connections**

#### 1.2 Create New GitHub Service Connection

1. Click **New service connection**
2. Select **GitHub** from the list
3. Choose authentication method:
   - **GitHub App** (Recommended for organizations)
   - **Personal Access Token** (Individual repositories)
   - **OAuth** (Interactive authentication)

#### 1.3 Configure GitHub App Authentication (Recommended)

1. Select **GitHub App**
2. Click **Install GitHub App** 
3. You'll be redirected to GitHub to install the Azure Pipelines app
4. Select the organization/repositories you want to grant access to
5. Return to Azure DevOps and complete the connection setup
6. **Service connection name**: Use a descriptive name like `GitHub-{OrgName}-Connection`
7. **Description**: `GitHub connection for migrated repositories`
8. Click **Save**

#### 1.4 Configure Personal Access Token Authentication

If using PAT authentication:

1. Select **Personal Access Token**
2. **Server URL**: `https://github.com`
3. **Personal Access Token**: Enter your GitHub PAT with these scopes:
   - `repo` (Full control of private repositories)
   - `admin:repo_hook` (Admin access to repository hooks) 
   - `read:org` (Read org membership)
4. **Service connection name**: `GitHub-PAT-Connection`
5. Click **Verify and save**

### Step 2: Update Pipeline Repository Sources

For each pipeline that needs to point to GitHub:

#### 2.1 Navigate to Pipeline

1. Go to **Pipelines** > **Pipelines**
2. Select the pipeline you need to update
3. Click **Edit**

#### 2.2 Update YAML Pipeline Repository

For YAML pipelines:

1. In the pipeline editor, locate the `resources` section or add one:

```yaml
resources:
  repositories:
  - repository: self
    type: git
    connection: GitHub-{OrgName}-Connection  # Your service connection name
    name: {github-org}/{repo-name}
    ref: refs/heads/main  # or your default branch
```

2. If the pipeline uses multiple repositories, update each one:

```yaml
resources:
  repositories:
  - repository: primary-repo
    type: git
    connection: GitHub-{OrgName}-Connection
    name: {github-org}/{primary-repo-name}
  - repository: shared-libs
    type: git
    connection: GitHub-{OrgName}-Connection
    name: {github-org}/{shared-libraries-repo}
```

3. Update any checkout steps:

```yaml
steps:
- checkout: self
- checkout: shared-libs  # If using multiple repositories
```

#### 2.3 Update Classic Pipeline Repository

For Classic (visual) pipelines:

1. In pipeline editor, go to **Get sources** tab
2. Change **Source type** from **Azure Repos Git** to **GitHub**
3. **Service connection**: Select your GitHub service connection
4. **Repository**: Select the migrated repository
5. **Default branch**: Update to match your GitHub repository's default branch
6. **Clean**: Set to `true` if you want clean checkouts
7. Click **Save**

#### 2.4 Update Trigger Settings

Update repository triggers:

1. In pipeline editor, go to **Triggers** tab
2. **Continuous integration**: 
   - Enable if you want builds on code changes
   - Update **Branch filters** to match GitHub branch names
3. **Pull request validation**:
   - Enable if you want PR builds
   - Update **Branch filters** for PR target branches
4. **Path filters**: Update any path-based triggers if repository structure changed

### Step 3: Update Variable Groups and Libraries

#### 3.1 Review Variable Groups

1. Navigate to **Pipelines** > **Library**
2. For each Variable Group used by your pipelines:
   - Click on the Variable Group name
   - Review variables for repository-specific references
   - Update any variables containing:
     - Repository URLs
     - Branch names
     - File paths
     - Service endpoints

#### 3.2 Update Repository-Specific Variables

Common variables to update:

```
# Before (Azure DevOps)
REPO_URL = https://dev.azure.com/{org}/{project}/_git/{repo}
BUILD_REPOSITORY_URI = https://dev.azure.com/{org}/{project}/_git/{repo}
SYSTEM_TEAMFOUNDATIONCOLLECTIONURI = https://dev.azure.com/{org}/

# After (GitHub)
REPO_URL = https://github.com/{org}/{repo}
BUILD_REPOSITORY_URI = https://github.com/{org}/{repo}.git
GITHUB_REPOSITORY = {org}/{repo}
```

#### 3.3 Update Pipeline Permissions

1. In Variable Group settings, verify **Pipeline permissions**
2. Ensure all relevant pipelines have access
3. Update **Security** settings if needed

### Step 4: Update Build and Release Pipelines

#### 4.1 Build Pipelines

For each build pipeline:

1. **Repository Configuration**: Follow Step 2 above
2. **Build Tasks**: Review tasks that reference repository paths:
   - **Copy Files** tasks with source paths
   - **PowerShell/Bash** scripts with hardcoded paths  
   - **Docker** tasks with context paths
3. **Artifacts**: Verify artifact publishing paths are still valid
4. **Test Results**: Update test result file paths if changed

#### 4.2 Release Pipelines

For each release pipeline:

1. **Artifacts**: 
   - If using repository artifacts, update source repository
   - Update **Default version** settings
   - Verify **Continuous deployment triggers**
2. **Stages**: Review each deployment stage:
   - Update any repository checkout tasks
   - Verify file copy operations
   - Update configuration file paths
3. **Variables**: Update stage-specific variables referencing repositories

### Step 5: Update Environments and Approvals

#### 5.1 Review Environments

1. Navigate to **Pipelines** > **Environments**
2. For each environment used by your pipelines:
   - Verify **Approvals and checks** still reference correct resources
   - Update any **Branch control** policies to use GitHub branches
   - Review **Security** settings for correct permissions

#### 5.2 Update Branch Policies

If using branch policies that reference repositories:

1. **Business hours**: Ensure time zones are appropriate
2. **Required reviewers**: Update if reviewer access has changed
3. **Build validation**: Point to updated pipelines

### Step 6: Test Pipeline Configuration

#### 6.1 Pipeline Validation Test

Create a comprehensive test to validate your pipeline configuration:

```yaml
# pipeline-validation-test.yml
name: Pipeline Configuration Validation

trigger: none  # Manual trigger only for testing

variables:
  - group: shared-variables  # Your updated variable group

pool:
  vmImage: 'ubuntu-latest'

stages:
- stage: ValidationTests
  displayName: 'Validate Pipeline Configuration'
  jobs:
  - job: RepositoryValidation
    displayName: 'Repository Access Validation'
    steps:
    
    # Test 1: Repository Checkout
    - checkout: self
      displayName: 'Test Repository Checkout'
      
    # Test 2: Verify Repository URL
    - bash: |
        echo "Repository URL: $(Build.Repository.Uri)"
        echo "Repository Name: $(Build.Repository.Name)"
        echo "Branch: $(Build.SourceBranchName)"
        echo "Commit: $(Build.SourceVersion)"
        
        # Verify we're connected to GitHub
        if [[ "$(Build.Repository.Uri)" == *"github.com"* ]]; then
          echo "✓ Repository correctly points to GitHub"
        else
          echo "✗ Repository does not point to GitHub"
          exit 1
        fi
      displayName: 'Validate Repository Connection'
      
    # Test 3: File System Verification
    - bash: |
        echo "Current directory contents:"
        ls -la
        
        # Test if we can access expected files
        if [ -f "README.md" ] || [ -f "readme.md" ]; then
          echo "✓ Repository files accessible"
        else
          echo "⚠ No README found - verify repository structure"
        fi
        
        echo "Git status:"
        git status
        git remote -v
      displayName: 'Verify Repository Files'
      
    # Test 4: Variable Group Access
    - bash: |
        echo "Testing variable group access..."
        # Replace these with your actual variables
        echo "Sample variable value: $(YourVariableName)"
        
        if [ -n "$(YourVariableName)" ]; then
          echo "✓ Variable group accessible"
        else
          echo "✗ Variable group not accessible"
          exit 1
        fi
      displayName: 'Test Variable Group Access'
      
    # Test 5: Service Connection Test
    - task: PowerShell@2
      inputs:
        targetType: 'inline'
        script: |
          Write-Host "Service Connection Test"
          Write-Host "Repository Provider: $(Build.Repository.Provider)"
          Write-Host "Repository ID: $(Build.Repository.ID)"
          
          if ("$(Build.Repository.Provider)" -eq "GitHub") {
            Write-Host "✓ Service connection working correctly"
          } else {
            Write-Host "✗ Service connection issue detected"
            exit 1
          }
      displayName: 'Test Service Connection'

  - job: ArtifactTest
    displayName: 'Artifact and Build Output Test'
    steps:
    - checkout: self
    
    # Test 6: Build Output Creation
    - bash: |
        mkdir -p $(Build.ArtifactStagingDirectory)/test-artifacts
        echo "Test build output" > $(Build.ArtifactStagingDirectory)/test-artifacts/build-test.txt
        echo "Build completed successfully" > $(Build.ArtifactStagingDirectory)/test-artifacts/status.log
      displayName: 'Create Test Artifacts'
      
    # Test 7: Publish Test Artifacts
    - task: PublishBuildArtifacts@1
      inputs:
        pathtoPublish: '$(Build.ArtifactStagingDirectory)/test-artifacts'
        artifactName: 'ValidationTestArtifacts'
        publishLocation: 'Container'
      displayName: 'Test Artifact Publishing'
      
    # Test 8: Test Results Publishing (if applicable)
    - bash: |
        mkdir -p test-results
        echo '<?xml version="1.0" encoding="UTF-8"?>
        <testsuites>
          <testsuite name="ValidationTests" tests="1" failures="0">
            <testcase name="ConfigurationTest" />
          </testsuite>
        </testsuites>' > test-results/validation-results.xml
      displayName: 'Generate Mock Test Results'
      
    - task: PublishTestResults@2
      inputs:
        testResultsFormat: 'JUnit'
        testResultsFiles: 'test-results/validation-results.xml'
        testRunTitle: 'Pipeline Validation Tests'
      displayName: 'Test Result Publishing'

- stage: EnvironmentTest
  displayName: 'Environment Configuration Test'
  dependsOn: ValidationTests
  condition: succeeded()
  jobs:
  - deployment: TestDeployment
    displayName: 'Test Environment Access'
    environment: 'development'  # Replace with your environment name
    strategy:
      runOnce:
        deploy:
          steps:
          - bash: |
              echo "✓ Environment deployment test successful"
              echo "Environment: $(Environment.Name)"
              echo "Resource: $(Environment.ResourceName)"
            displayName: 'Environment Connectivity Test'
```

#### 6.2 Running the Validation Test

1. **Create the test pipeline**:
   - Save the above YAML as `pipeline-validation-test.yml` in your repository
   - Create a new pipeline in Azure DevOps using this YAML file

2. **Update the test configuration**:
   - Replace `shared-variables` with your actual variable group name
   - Replace `YourVariableName` with a variable from your variable group
   - Replace `development` with your actual environment name
   - Add additional tests specific to your pipeline requirements

3. **Run the test**:
   - Manually trigger the validation pipeline
   - Monitor the output for any failures
   - Review the test results and artifacts

4. **Interpret results**:
   - ✓ Green checkmarks indicate successful configuration
   - ✗ Red X marks indicate configuration issues that need attention
   - ⚠ Warnings indicate potential issues to investigate

#### 6.3 Production Pipeline Testing

After validation tests pass:

1. **Incremental testing**: Test one production pipeline at a time
2. **Monitor first runs**: Closely monitor initial production pipeline runs
3. **Rollback plan**: Keep original pipeline configurations available for quick rollback
4. **Team communication**: Notify team of pipeline changes and testing schedule

### Step 7: Batch Pipeline Updates

For organizations with hundreds of pipelines, use these strategies:

#### 7.1 PowerShell Automation Script

Create a script to update multiple pipelines programmatically:

```powershell
# bulk-pipeline-update.ps1
param(
    [string]$Organization = "your-org",
    [string]$Project = "your-project",
    [string]$PAT = $env:AZURE_DEVOPS_PAT,
    [string]$GitHubServiceConnection = "GitHub-Connection",
    [string]$GitHubOrg = "your-github-org",
    
    # Subset filtering options
    [string[]]$PipelineNames = @(),           # Specific pipeline names to update
    [string[]]$PipelineIds = @(),             # Specific pipeline IDs to update
    [string]$NamePattern = "",                # Pattern to match pipeline names (e.g., "*api*", "prod-*")
    [int]$MaxPipelines = 0,                   # Maximum number of pipelines to process (0 = all)
    [switch]$TestMode = $false,               # Test mode - only show what would be updated
    [string]$LogFile = "pipeline-update-log.txt"  # Log file for tracking changes
)

# Set up authentication
$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$($PAT)"))
$headers = @{Authorization = ("Basic {0}" -f $base64AuthInfo)}

# Initialize logging
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logPath = "$LogFile.$timestamp"
$updateLog = @()

function Write-LogEntry {
    param($Message, $Color = "White")
    $logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message"
    Write-Host $logEntry -ForegroundColor $Color
    $script:updateLog += $logEntry
}

# Get all pipelines
$pipelinesUrl = "https://dev.azure.com/$Organization/$Project/_apis/pipelines?api-version=6.0"
$allPipelines = Invoke-RestMethod -Uri $pipelinesUrl -Headers $headers -Method Get

Write-LogEntry "Found $($allPipelines.count) total pipelines in project"

# Filter pipelines based on criteria
$filteredPipelines = $allPipelines.value

# Apply specific pipeline ID filter
if ($PipelineIds.Count -gt 0) {
    $filteredPipelines = $filteredPipelines | Where-Object { $_.id -in $PipelineIds }
    Write-LogEntry "Filtered by IDs: $($PipelineIds -join ', ') - $($filteredPipelines.Count) pipelines match"
}

# Apply specific pipeline name filter
if ($PipelineNames.Count -gt 0) {
    $filteredPipelines = $filteredPipelines | Where-Object { $_.name -in $PipelineNames }
    Write-LogEntry "Filtered by names: $($PipelineNames -join ', ') - $($filteredPipelines.Count) pipelines match"
}

# Apply name pattern filter
if ($NamePattern) {
    $filteredPipelines = $filteredPipelines | Where-Object { $_.name -like $NamePattern }
    Write-LogEntry "Filtered by pattern '$NamePattern' - $($filteredPipelines.Count) pipelines match"
}

# Apply max pipelines limit
if ($MaxPipelines -gt 0 -and $filteredPipelines.Count -gt $MaxPipelines) {
    $filteredPipelines = $filteredPipelines | Select-Object -First $MaxPipelines
    Write-LogEntry "Limited to first $MaxPipelines pipelines"
}

Write-LogEntry "Processing $($filteredPipelines.Count) pipelines..." -Color "Cyan"

if ($TestMode) {
    Write-LogEntry "=== TEST MODE - NO CHANGES WILL BE MADE ===" -Color "Yellow"
}

$processedCount = 0
$updatedCount = 0
$errorCount = 0

foreach ($pipeline in $filteredPipelines) {
    $processedCount++
    Write-LogEntry "[$processedCount/$($filteredPipelines.Count)] Processing pipeline: $($pipeline.name) (ID: $($pipeline.id))"
    
    try {
        # Get pipeline definition
        $pipelineUrl = "https://dev.azure.com/$Organization/$Project/_apis/pipelines/$($pipeline.id)?api-version=6.0"
        $pipelineDetail = Invoke-RestMethod -Uri $pipelineUrl -Headers $headers -Method Get
        
        # Check if pipeline uses Azure Repos
        if ($pipelineDetail.configuration.repository.type -eq "azureReposGit") {
            Write-LogEntry "  - Pipeline uses Azure Repos, needs updating" -Color "White"
            
            if ($TestMode) {
                Write-LogEntry "  - [TEST MODE] Would update repository source to GitHub" -Color "Yellow"
                $updatedCount++
            } else {
                # Update repository configuration
                $originalRepoName = $pipelineDetail.configuration.repository.name
                $pipelineDetail.configuration.repository.type = "gitHub"
                $pipelineDetail.configuration.repository.connection.id = $GitHubServiceConnection
                
                # Extract repo name from current URL and map to GitHub
                $currentRepoName = $pipelineDetail.configuration.repository.name.Split('/')[-1]
                $pipelineDetail.configuration.repository.name = "$GitHubOrg/$currentRepoName"
                
                Write-LogEntry "  - Updating: $originalRepoName -> $GitHubOrg/$currentRepoName"
                
                # Update pipeline
                $updateUrl = "https://dev.azure.com/$Organization/$Project/_apis/pipelines/$($pipeline.id)?api-version=6.0"
                Invoke-RestMethod -Uri $updateUrl -Headers $headers -Method Put -Body ($pipelineDetail | ConvertTo-Json -Depth 10) -ContentType "application/json"
                Write-LogEntry "  ✓ Pipeline updated successfully" -Color "Green"
                $updatedCount++
            }
        }
        else {
            Write-LogEntry "  - Pipeline already configured for non-Azure Repos source (Type: $($pipelineDetail.configuration.repository.type))" -Color "Yellow"
        }
    }
    catch {
        $errorCount++
        Write-LogEntry "  ✗ Failed to update pipeline: $($_.Exception.Message)" -Color "Red"
    }
    
    # Small delay to avoid overwhelming the API
    Start-Sleep -Milliseconds 500
}

# Summary
Write-LogEntry "" 
Write-LogEntry "=== UPDATE SUMMARY ===" -Color "Cyan"
Write-LogEntry "Pipelines processed: $processedCount" -Color "White"
Write-LogEntry "Pipelines updated: $updatedCount" -Color "Green"
Write-LogEntry "Errors encountered: $errorCount" -Color $(if($errorCount -gt 0) {"Red"} else {"Green"})

if ($TestMode) {
    Write-LogEntry "NOTE: Test mode was enabled - no actual changes were made" -Color "Yellow"
}

# Save log to file
$updateLog | Out-File -FilePath $logPath -Encoding UTF8
Write-LogEntry "Log saved to: $logPath" -Color "Cyan"
```

#### 7.2 Using the Script with Subset Filtering

1. **Prepare environment**:
   ```powershell
   # Set environment variables
   $env:AZURE_DEVOPS_PAT = "your-pat-token"
   ```

2. **Test with specific pipelines first**:
   ```powershell
   # Test mode - see what would be updated without making changes
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" -TestMode
   
   # Update only specific pipelines by name
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -PipelineNames @("MyApp-CI", "MyApp-Release", "Database-Migration")
   
   # Update only specific pipelines by ID
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -PipelineIds @(123, 456, 789)
   ```

3. **Pattern-based filtering**:
   ```powershell
   # Update all pipelines containing "api" in their name
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "*api*"
   
   # Update all production pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "prod-*"
   
   # Update all development/test pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "*dev*", "*test*"
   ```

4. **Limit number of pipelines processed**:
   ```powershell
   # Process only first 5 pipelines (good for initial testing)
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -MaxPipelines 5
   
   # Test mode with first 10 pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -MaxPipelines 10 -TestMode
   ```

5. **Recommended phased approach**:
   ```powershell
   # Phase 1: Test mode to see what would be changed
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -TestMode -MaxPipelines 10
   
   # Phase 2: Update 5 non-critical pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "*dev*" -MaxPipelines 5
   
   # Phase 3: Update test/staging pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "*test*", "*staging*"
   
   # Phase 4: Update production pipelines (after validation)
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org" `
       -NamePattern "*prod*"
   
   # Phase 5: Update remaining pipelines
   .\bulk-pipeline-update.ps1 -Organization "your-org" -Project "your-project" -GitHubOrg "your-github-org"
   ```

6. **Logging and tracking**:
   ```powershell
   # Custom log file name
   .\bulk-pipeline-update.ps1 -LogFile "pipeline-migration-phase1"
   
   # The script automatically timestamps log files:
   # pipeline-migration-phase1.2024-01-15_14-30-22
   ```

### Step 7: Monitoring and Validation

#### 7.1 Pipeline Run Monitoring

After updating pipelines, monitor for:

- **Build success rates**: Compare pre/post migration success rates
- **Build duration**: Monitor for performance changes
- **Artifact publishing**: Ensure artifacts are being created correctly
- **Test execution**: Verify test results are being published
- **Deployment success**: Monitor release pipeline success rates

#### 7.2 Create Monitoring Dashboard

Set up monitoring dashboards to track pipeline health using your existing infrastructure:

##### Option 1: Elastic Stack + Grafana (Recommended)

Since you're using Elastic & Grafana, here's how to set up comprehensive pipeline monitoring:

**Step 1: Configure Azure DevOps Data Collection**

Create a data pipeline to send Azure DevOps metrics to Elasticsearch:

```json
{
  "pipeline_monitoring": {
    "data_sources": [
      {
        "name": "azure_devops_builds",
        "type": "azure_devops_api",
        "endpoint": "https://dev.azure.com/{org}/{project}/_apis/build/builds",
        "fields": [
          "id", "buildNumber", "status", "result", 
          "queueTime", "startTime", "finishTime",
          "repository.name", "repository.type", "sourceBranch"
        ]
      },
      {
        "name": "azure_devops_releases",
        "type": "azure_devops_api", 
        "endpoint": "https://dev.azure.com/{org}/{project}/_apis/release/releases",
        "fields": [
          "id", "name", "status", "createdOn", "modifiedOn",
          "environments[].name", "environments[].status"
        ]
      }
    ],
    "collection_interval": "5m"
  }
}
```

**Step 2: Logstash Configuration for Azure DevOps Data**

```ruby
# logstash-azure-devops.conf
input {
  http_poller {
    urls => {
      builds => {
        method => get
        url => "https://dev.azure.com/${AZURE_ORG}/${AZURE_PROJECT}/_apis/build/builds"
        headers => {
          Authorization => "Basic ${AZURE_PAT_BASE64}"
        }
        codec => "json"
      }
    }
    request_timeout => 60
    interval => 300
    metadata_target => "http_poller_metadata"
  }
}

filter {
  # Parse Azure DevOps build data
  if [http_poller_metadata][name] == "builds" {
    split { field => "[value]" }
    
    mutate {
      add_field => {
        "pipeline_id" => "%{[value][definition][id]}"
        "pipeline_name" => "%{[value][definition][name]}"
        "build_status" => "%{[value][status]}"
        "build_result" => "%{[value][result]}"
        "repository_type" => "%{[value][repository][type]}"
        "repository_name" => "%{[value][repository][name]}"
        "source_branch" => "%{[value][sourceBranch]}"
      }
    }
    
    # Add migration status tag
    if [repository_type] == "GitHub" {
      mutate { add_tag => "migrated_to_github" }
    } else if [repository_type] == "TfsGit" {
      mutate { add_tag => "azure_repos" }
    }
    
    date {
      match => [ "[value][finishTime]", "ISO8601" ]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["${ELASTICSEARCH_HOST}:9200"]
    index => "azure-devops-pipelines-%{+YYYY.MM.dd}"
  }
}
```

**Step 3: Grafana Dashboard Configuration**

Create a comprehensive Grafana dashboard with these panels:

```json
{
  "dashboard": {
    "title": "Azure DevOps Pipeline Migration Monitoring",
    "panels": [
      {
        "title": "Pipeline Success Rate by Repository Type",
        "type": "stat",
        "targets": [{
          "query": "SELECT \n  COUNT(CASE WHEN build_result = 'succeeded' THEN 1 END) * 100.0 / COUNT(*) as success_rate,\n  repository_type\nFROM azure-devops-pipelines-*\nWHERE $__timeFilter(timestamp)\nGROUP BY repository_type"
        }]
      },
      {
        "title": "Migrated vs Non-Migrated Pipeline Performance",
        "type": "timeseries",
        "targets": [{
          "query": "SELECT \n  histogram_quantile(0.95, build_duration) as p95_duration,\n  repository_type\nFROM azure-devops-pipelines-*\nWHERE $__timeFilter(timestamp)\nGROUP BY time($__interval), repository_type"
        }]
      },
      {
        "title": "Build Failures by Repository Type",
        "type": "table",
        "targets": [{
          "query": "SELECT \n  pipeline_name,\n  repository_type,\n  COUNT(*) as failure_count\nFROM azure-devops-pipelines-*\nWHERE build_result = 'failed' AND $__timeFilter(timestamp)\nGROUP BY pipeline_name, repository_type\nORDER BY failure_count DESC\nLIMIT 20"
        }]
      }
    ]
  }
}
```

##### Option 2: GitHub Actions Integration (If needed)

If you want to monitor from the GitHub side as well:

**Step 1: GitHub Actions Workflow for Monitoring**

```yaml
# .github/workflows/pipeline-health-monitor.yml
name: Pipeline Health Monitor

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  monitor-azure-pipelines:
    runs-on: ubuntu-latest
    steps:
    - name: Check Azure DevOps Pipeline Status
      run: |
        # Query Azure DevOps API for recent builds
        BUILDS=$(curl -u ":${{ secrets.AZURE_DEVOPS_PAT }}" \
          "https://dev.azure.com/${{ vars.AZURE_ORG }}/${{ vars.AZURE_PROJECT }}/_apis/build/builds?api-version=6.0&\$top=50")
        
        # Count failed builds in last hour
        FAILED_COUNT=$(echo "$BUILDS" | jq '[.value[] | select(.finishTime > (now - 3600 | strftime("%Y-%m-%dT%H:%M:%S.%fZ")) and .result == "failed")] | length')
        
        echo "Failed builds in last hour: $FAILED_COUNT"
        
        # Set up alerts if failure rate is high
        if [ "$FAILED_COUNT" -gt 5 ]; then
          echo "::warning::High failure rate detected: $FAILED_COUNT failed builds in last hour"
        fi
        
    - name: Send to Monitoring System
      if: env.ELASTIC_ENDPOINT
      run: |
        # Send metrics to your Elastic/Grafana stack
        curl -X POST "${{ secrets.ELASTIC_ENDPOINT }}/github-monitoring/_doc" \
          -H "Content-Type: application/json" \
          -d "{
            \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\",
            \"source\": \"github-actions\",
            \"azure_pipeline_failures\": $FAILED_COUNT,
            \"monitoring_run_id\": \"${{ github.run_id }}\"
          }"
```

##### Recommended Approach for Your Setup

Since you already have **Elastic & Grafana**, I recommend **Option 1** (Elastic Stack + Grafana) because:

1. **Leverage existing infrastructure**: Use your current monitoring stack
2. **Comprehensive metrics**: Track both Azure DevOps and GitHub metrics
3. **Custom alerting**: Set up alerts for pipeline failures or performance degradation
4. **Historical analysis**: Keep long-term data for trend analysis
5. **Team familiarity**: Your team already knows Grafana dashboards

### Step 8: Rollback Procedures

Prepare rollback procedures in case issues arise:

#### 8.1 Pipeline Rollback

1. **Backup original configurations**: Export pipeline definitions before changes
2. **Rollback script**: Create script to revert repository sources
3. **Quick rollback**: Identify critical pipelines that need fastest rollback
4. **Team communication**: Prepare communication plan for rollback scenarios

#### 8.2 Service Connection Management

1. **Preserve original connections**: Keep Azure Repos connections active during transition
2. **Gradual migration**: Move pipelines in phases rather than all at once
3. **Connection testing**: Regularly test both old and new connections

### Troubleshooting Common Issues

#### Issue 1: Service Connection Authentication Failures

**Symptoms**: Pipeline fails with authentication errors

**Solutions**:
1. Verify GitHub PAT has correct scopes
2. Check if GitHub App installation covers the repository
3. Ensure service connection is authorized for the pipeline
4. Verify repository permissions in GitHub

#### Issue 2: Repository Not Found

**Symptoms**: Pipeline fails to checkout repository

**Solutions**:
1. Verify repository name matches exactly (case sensitive)
2. Check if repository is public/private and permissions are correct  
3. Ensure service connection has access to the repository
4. Verify GitHub organization name is correct

#### Issue 3: Branch Reference Failures

**Symptoms**: Pipeline cannot find specified branch

**Solutions**:
1. Update default branch references (master → main)
2. Check if branch protection rules block pipeline access
3. Verify branch naming conventions match
4. Update trigger branch filters

#### Issue 4: Variable Group Access

**Symptoms**: Variables are empty or undefined in pipeline

**Solutions**:
1. Verify variable group permissions for the pipeline
2. Check variable group security settings
3. Ensure variable names haven't changed
4. Test variable access with simple echo commands

#### Issue 5: Environment Deployment Failures  

**Symptoms**: Deployment stages fail to access environments

**Solutions**:
1. Verify environment permissions and approvals
2. Check deployment group agent connectivity
3. Update environment resource configurations
4. Review deployment gate conditions

### Best Practices Summary

1. **Phased Approach**: Update pipelines in small batches to minimize risk
2. **Testing First**: Always test with validation pipeline before production updates
3. **Documentation**: Maintain an inventory of updated pipelines and their status
4. **Rollback Ready**: Keep rollback procedures tested and available
5. **Team Communication**: Keep teams informed of changes and timelines
6. **Monitoring**: Set up proactive monitoring for pipeline health
7. **Security**: Regularly rotate PATs and review service connection permissions
8. **Automation**: Use scripts for bulk updates but validate results manually

Following these comprehensive steps will ensure your Azure DevOps pipelines are properly configured to work with your migrated GitHub repositories while maintaining reliability and security.

---

## Additional Resources

- **[📖 Complete README](../../README.md)** - Full project documentation with all features
- **[✅ Pre-Migration Checklist](PRE_MIGRATION_CHECKLIST.md)** - 100+ validation items before migration  
- **[🧪 Testing Guide](TESTING.md)** - Comprehensive testing procedures
- **[⚙️ Configuration Reference](../technical/configuration.md)** - Complete configuration options
- **[🔍 Troubleshooting Guide](../technical/troubleshooting.md)** - Problem resolution and debugging
- **[🔌 API Documentation](../technical/api.md)** - Technical API reference