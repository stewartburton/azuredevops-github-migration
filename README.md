# Azure DevOps to GitHub Migration Tool

> TL;DR (Jira Mode – code & pipelines only, no work items)
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

A comprehensive Python tool for migrating repositories, work items, and other artifacts from Azure DevOps to GitHub.

## 📦 Installation

### PyPI Installation (Recommended)
```bash
# Install from PyPI
pip install azuredevops-github-migration

# Verify installation
azuredevops-github-migration --version

# Get help
azuredevops-github-migration --help
```

### Development Installation
```bash
# Clone and install in development mode
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration
pip install -e .
```

## Features

- **Repository Migration**: Clone and migrate Git repositories from Azure DevOps to GitHub with complete history
- **Pipeline Conversion**: Convert Azure DevOps pipelines to GitHub Actions workflows
- **Pipeline Scope Control**: Limit pipeline conversion to only those bound to the repository (`--pipelines-scope repository`) or include all project pipelines (default)
- **Exclude Disabled Pipelines**: Skip disabled/paused pipelines with `--exclude-disabled-pipelines`
- **Work Items to Issues** (Optional): Convert Azure DevOps work items to GitHub issues - skip if using Jira/other issue tracking
- **Jira Mode / Work Item Suppression**: Use `--skip-work-items` during analysis (or a config with `migrate_work_items=false`) to automatically disable issue migration and omit work item fields from reports & plans
- **Optional Remote Verification**: Post-push branch comparison with `--verify-remote` to ensure remote & local branches match
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

### Option 1: Install from PyPI (Recommended)
```bash
# Install the latest stable version
pip install azuredevops-github-migration

# Verify installation
azuredevops-github-migration --version

# Create configuration from template
azuredevops-github-migration init --template jira-users  # For Jira users (most common)
# OR
azuredevops-github-migration init --template full        # Complete migration setup
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

### Option 3: Manual Development Setup
```bash
# Clone and install in development mode
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration

# Install in development mode
pip install -e .

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
azuredevops-github-migration migrate --validate-only --config config.json

# 2. Analyze your organization (optional)
azuredevops-github-migration analyze --create-plan --config config.json

# 3. Test migration (safe, no changes)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json

# 4. Actual migration (Jira users - most common)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-issues --config config.json

# Repository-only pipelines (instead of all project pipelines)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# Exclude disabled pipelines & verify remote branches post-push
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --verify-remote --config config.json

# 5. Batch migration
azuredevops-github-migration batch --plan migration_plan.json --config config.json
```

#### Alternative Commands (Development/Source Installation)
```bash
# If installed from source, you can also use:
python -m azuredevops_github_migration.migrate --project "MyProject" --repo "my-repo" --config config.json
python -m azuredevops_github_migration.analyze --create-plan --config config.json
python -m azuredevops_github_migration.batch_migrate --plan migration_plan.json --config config.json
```

### Jira Mode (Skip Work Items Completely)

If you manage issues in Jira, you can fully suppress work item processing:

```bash
# Initialize with Jira-focused config (sets migrate_work_items=false)
azuredevops-github-migration init --template jira-users

# Analyze a specific project without querying or including work item data
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items

# OR analyze entire organization (work items omitted)
azuredevops-github-migration analyze --create-plan --config config.json --skip-work-items

# Dry run a repo (issue migration auto-disabled; no need for --no-issues)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json

# Actual migration (issues suppressed automatically)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json

# Batch dry run (plan produced by --skip-work-items omits migrate_issues fields)
azuredevops-github-migration batch --plan migration_plan_<org>_*.json --dry-run --config config.json

# Batch execute
azuredevops-github-migration batch --plan migration_plan_<org>_*.json --config config.json
```

Notes:
* `--skip-work-items` both avoids Work Item API calls and removes work item statistics & `migrate_issues` flags from the analysis output and plan.
* In batch mode: if a plan omits `migrate_issues`, the tool defaults those entries to `False`.
* In single migrations: if your config has `"migrate_work_items": false`, issues are auto-disabled (even without `--no-issues`). Add `--no-issues` only for explicit clarity.

## Configuration

### Environment Variables

Create a `.env` file with your authentication tokens:

```bash
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

### Migration Config

Edit `config.json` to configure:

- Azure DevOps organization and authentication
- GitHub organization and settings  
- Work item type mappings
- State mappings
- Rate limiting settings
- Logging configuration

See the [Configuration Reference](docs/technical/configuration.md) for complete options.

## Scripts Overview

### `migrate` - Main Migration Command

Single repository migration with full control over the process.

```bash
# Basic usage
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json

# Custom GitHub repo name
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --github-repo "new-name" --config config.json

# Skip work item migration
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-issues --config config.json

# Limit pipelines to the repository & exclude disabled, with remote verification
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --pipelines-scope repository --exclude-disabled-pipelines --verify-remote --config config.json
```

### `analyze` - Organization Analyzer

Analyze your Azure DevOps organization to understand what needs to be migrated.

```bash
# Analyze entire organization
azuredevops-github-migration analyze --create-plan --config config.json

# Analyze specific project
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json

# Jira mode (omit & skip work items)
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items

# Export as CSV
azuredevops-github-migration analyze --format csv --config config.json
```

### `batch` - Batch Migration

Migrate multiple repositories using a migration plan.

```bash
# Create sample migration plan
azuredevops-github-migration batch --create-sample

# Dry run to see what would be migrated (uses default plan name)
azuredevops-github-migration batch --dry-run --config config.json

# Execute batch migration with explicit plan
azuredevops-github-migration batch --plan migration_plan.json --config config.json
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
- Repository-level filtering and disabled pipeline exclusion available

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
- Code review comments

❌ **Azure DevOps specific features:**
- Wiki pages
- Test plans and cases
- Boards configuration
- Extensions and customizations
- Work item attachments (files)
- Build/Release pipeline history (only YAML definitions are converted)

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

Use least privilege. Start with the minimum scopes and add only if the tool reports an authorization error for a feature you actually need. Fine‑grained tokens (GitHub) and short‑lived PATs (Azure DevOps) are preferred where possible.

### Required Personal Access Token (PAT) Scopes

#### Azure DevOps PAT
Minimum (repository migration only – no work items):
- Code: Read (clone repositories, enumerate branches/tags)
- Project and Team: Read (list projects & repos)

Add ONLY if needed:
- Work Items: Read (when converting work items to GitHub issues; omit when using `--no-issues` or Jira)
- Code: Read & Write (only if you intentionally push changes back to Azure DevOps – not required for one‑way migration)
- Other scopes (Packaging, Build, Release, Test) are NOT required unless you extend the tool to cover those assets.

#### GitHub PAT
Minimum (target repos already exist or created manually):
- repo (covers contents, issues, pulls for private & public repos)

Add ONLY if needed:
- admin:org (tool needs to create new repositories inside an organization)
- delete_repo (you implement rollback that deletes created repos)
- workflow (you programmatically manipulate Actions runs beyond committing YAML files)
- read:user (optional; basic profile lookups – not required for migration)

Avoid broader scopes (e.g. admin:enterprise) unless explicitly justified.

### Scenario Scope Matrix
| Scenario | Azure DevOps Scopes | GitHub Scopes |
|----------|---------------------|---------------|
| Single repo, no issues | Code (Read), Project & Team (Read) | repo |
| Repo + work items | Code (Read), Project & Team (Read), Work Items (Read) | repo |
| Batch migrate multiple repos | Code (Read), Project & Team (Read) | repo |
| Auto create org repos | Code (Read), Project & Team (Read) | repo, admin:org |
| Rollback deletes repos | Code (Read), Project & Team (Read) | repo, delete_repo |

### Obtaining Tokens
Below are explicit steps to create the required Personal Access Tokens.

#### Azure DevOps (Create PAT)
1. In any Azure DevOps page, click your avatar (top-right) → **User settings** → **Personal access tokens**.
2. Click **+ New Token**.
3. Fill in:
    - **Name**: e.g. `ado-migration-temp`.
    - **Organization**: (choose the source org).
    - **Expiration**: Short as practical (e.g. 30 or 60 days). For long batch waves, plan a rotation date.
4. Under **Scopes**, click **Custom defined** and select ONLY the scopes you need (see tables above):
    - Start with: Code (Read), Project and Team (Read).
    - Add Work Items (Read) ONLY if migrating issues.
    - Avoid adding Write unless you specifically push back to Azure DevOps.
5. Click **Create**.
6. Copy the token immediately (cannot be recovered later). Store it securely (secret manager, password vault, or environment variable injection). Do NOT commit it.
7. (Optional) Record the expiration date in your migration plan.

#### GitHub (Fine‑grained PAT – Recommended)
1. GitHub → **Settings** (profile) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Token name**: e.g. `gh-migration-fg`.
3. **Expiration**: Select a short duration (or custom) matching migration window.
4. **Resource owner**: Select the user or organization that owns the destination repositories.
5. **Repository access**: Choose specific repositories (preferred) or **All repositories** only if necessary. If creating new repos, ensure permission to do so (org-level admin rights or use classic token with admin:org if required).
6. **Permissions**: Under *Repository permissions* grant:
    - **Contents**: Read and write (required for pushing migrated history).
    - **Metadata**: Read (automatically included / required).
    - **Issues**: Read & write (only if migrating work items → GitHub issues; otherwise leave at Read or No access).
    - Additional (Actions, Administration) only if required by your scenario (e.g., repository creation may require classic token admin:org if fine‑grained lacks coverage in your context).
7. Generate token and copy it once. Store securely.

#### GitHub (Classic PAT – When Fine‑grained Not Suitable)
1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token**.
2. **Note**: Provide a descriptive name, set a short expiration.
3. Select scopes:
    - **repo** (includes repo:status, repo_deployment, public_repo, repo:invite — enough for code + issues).
    - **admin:org** ONLY if the tool itself will create repositories in the organization (and you have proper org role).
    - **delete_repo** ONLY if you will automate rollback deletion.
    - **workflow** ONLY if programmatically manipulating workflow runs beyond committing YAML.
4. Generate & copy once. Store securely; treat as a secret.

Choosing Between Fine‑grained vs Classic: Prefer fine‑grained; use classic only when you need composite scopes (e.g., admin:org + repo creation) not yet fully supported by fine‑grained tokens for your use case.

### Environment Variable Setup
Store tokens in environment variables or a local `.env` (never commit tokens).

PowerShell (Windows):
```powershell
$env:AZURE_DEVOPS_PAT = 'xxxxxxxxxxxxxxxxxxxxxxxx'
$env:GITHUB_TOKEN = 'ghp_xxxxxxxxxxxxxxxxxxxxx'
```

macOS / Linux (bash/zsh):
```bash
export AZURE_DEVOPS_PAT=xxxxxxxxxxxxxxxxxxxxxxxx
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
```

`.env` file example (ensure `.env` is in `.gitignore`):
```
AZURE_DEVOPS_PAT=xxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
```

### Verification Checklist
Run these steps; if a step fails, add only the missing scope:
1. Validate setup (`azuredevops-github-migration migrate --validate-only --config config.json`) → validates all credentials
2. Analyze / list projects (`azuredevops-github-migration analyze --create-plan --config config.json`) → validates Azure DevOps Code Read + Project & Team Read
3. Dry run repo migration (`azuredevops-github-migration migrate --dry-run --config config.json`) → validates Code Read
4. Work item fetch (if not using `--no-issues`) → validates Work Items Read
5. Repo creation in org (if configured) → validates admin:org
6. Push to GitHub (actual migration) → validates repo scope

After migration, narrow or revoke PATs if no ongoing synchronization is required.

## Migration Planning

### 1. Analysis Phase

```bash
azuredevops-github-migration analyze --create-plan --config config.json
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
azuredevops-github-migration batch --dry-run --plan your_plan.json --config config.json

# Execute migration
azuredevops-github-migration batch --plan your_plan.json --config config.json
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
- When `--verify-remote` is used, logs include remote vs local branch comparison (missing/extra branches)

## Key CLI Flags (Quick Reference)

| Flag | Purpose | Default |
|------|---------|---------|
| `--dry-run` | Simulate migration without side effects | off |
| `--no-issues` | Skip work item → issue conversion | off |
| `--no-pipelines` | Skip pipeline conversion | off |
| `--pipelines-scope {project|repository}` | Control pipeline selection scope | project |
| `--exclude-disabled-pipelines` | Omit disabled/paused pipelines | off |
| `--no-git` | Skip Git history migration | off |
| `--verify-remote` | Compare remote branch list to local after push | off |
| `--skip-work-items` (analyze) | Do not query work items; omit related fields & auto-disable issue migration later | off |
| `--debug` | Verbose logging | off |
| `--validate-only` | Validate config & credentials only | off |

Combine for precision, e.g.: 
```bash
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" \
    --pipelines-scope repository --exclude-disabled-pipelines --verify-remote --dry-run --config config.json
```

Automatic behaviors:
* If config contains `"migrate_work_items": false`, single repo migrations suppress issues without needing `--no-issues`.
* If a migration plan omits `migrate_issues` (produced via `--skip-work-items`), batch migration treats all entries as code-only.
* Use `--no-issues` for explicitness when communicating commands to others.

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