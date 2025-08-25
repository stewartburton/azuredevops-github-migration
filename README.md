# Azure DevOps to GitHub Migration Tool

A comprehensive Python tool for migrating repositories, work items, and other artifacts from Azure DevOps to GitHub.

## Features

- **Repository Migration**: Clone and migrate Git repositories from Azure DevOps to GitHub with complete history
- **Pipeline Conversion**: Convert Azure DevOps pipelines to GitHub Actions workflows
- **Pipeline Scope Control**: Limit pipeline conversion to only those bound to the repository (`--pipelines-scope repository`) or include all project pipelines (default)
- **Exclude Disabled Pipelines**: Skip disabled/paused pipelines with `--exclude-disabled-pipelines`
- **Work Items to Issues** (Optional): Convert Azure DevOps work items to GitHub issues - skip if using Jira/other issue tracking
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

# Repository-only pipelines (instead of all project pipelines)
python src/migrate.py --project "MyProject" --repo "my-repo" --pipelines-scope repository --config config.json

# Exclude disabled pipelines & verify remote branches post-push
python src/migrate.py --project "MyProject" --repo "my-repo" --exclude-disabled-pipelines --verify-remote --config config.json

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

# Limit pipelines to the repository & exclude disabled, with remote verification
python migrate.py --project "MyProject" --repo "my-repo" --pipelines-scope repository --exclude-disabled-pipelines --verify-remote
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
1. Analyze / list projects (`analyze.py --create-plan`) → validates Azure DevOps Code Read + Project & Team Read
2. Dry run repo migration (`migrate.py --dry-run`) → validates Code Read
3. Work item fetch (if not using `--no-issues`) → validates Work Items Read
4. Repo creation in org (if configured) → validates admin:org
5. Push to GitHub (actual migration) → validates repo scope

After migration, narrow or revoke PATs if no ongoing synchronization is required.

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
| `--debug` | Verbose logging | off |
| `--validate-only` | Validate config & credentials only | off |

Combine for precision, e.g.: `--pipelines-scope repository --exclude-disabled-pipelines --verify-remote --no-issues`.

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