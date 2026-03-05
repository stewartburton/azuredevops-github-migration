# Azure DevOps to GitHub Migration Tool

Production-ready CLI to migrate Azure DevOps repositories (and optionally work items & pipelines) to GitHub with safety, repeatability, and clear diagnostics.

> Need a fast Jira-mode (code + pipelines only)? See Quick Start below.

---

## Key Features

| Area | Capability |
|------|------------|
| Repositories | Full Git history (branches, tags, metadata) |
| Pipelines | Azure DevOps pipelines to GitHub Actions (temp directory, never written locally unless allowed) |
| Work Items (optional) | Map to GitHub issues (HTML to Markdown, type/state/priority to labels) |
| Batch Mode | Plan-driven multi-repo execution with concurrency, state tracking, and retry |
| Freeze / Unfreeze | Lock ADO repos via Security API before migration, restore after |
| State Management | Thread-safe JSON state with resume and retry support |
| Status Dashboard | CLI progress tracking with state file |
| Verification | Automated branch parity checks post-migration |
| Analysis | Inventory & migration planning report |
| Diagnostics | `doctor`, placeholder auto-append, interactive remediation & editor |
| Interactive UX | Arrow-key menu (`interactive`) with streamlined diagnostics & env actions |
| Project Selection UX | Paginated (10/page) quickstart project picker with search/filter (substring + fuzzy), jump to letter |
| Safety | Dry runs, rate limiting, retry logic, masked tokens |
| Reporting | JSON migration reports + verification script integration |
| Extensibility | Clean Python package layout, tests, semantic versioning |

---

## Quick Start

### Install from PyPI (Recommended)

```bash
pip install azuredevops-github-migration
azuredevops-github-migration --version
```

### Quickstart Wizard

First-time users: let the guided wizard chain initialization, environment setup, diagnostics, and a quick org discovery.

```bash
azuredevops-github-migration quickstart --template jira-users
```

| Flag | Purpose |
|------|---------|
| `--template full` | Use full (work items enabled) config template |
| `--skip-env` | Skip interactive env entry (if .env already populated) |
| `--skip-init` | Do not create config even if missing |
| `--no-analyze` | Skip project listing step |
| `--non-interactive` | Auto-advance without Y/n confirmations |
| `--no-project-select` | Disable interactive project selection (still prints list) |
| `--open-menu` | Automatically launch the interactive menu after the wizard |

### From Source

```bash
git clone https://github.com/stewartburton/azuredevops-github-migration.git
cd azuredevops-github-migration
pip install -e .
```

### Auto-Patch Behavior

If your existing `config.json` still contains legacy placeholders like `"your-organization-name"` or `"your-github-org"`, the wizard will (non-destructively) back up the file (e.g. `config.json.bak.<timestamp>`) and replace those fields with the values from `AZURE_DEVOPS_ORGANIZATION` / `GITHUB_ORGANIZATION` (or their aliases) when available. This prevents early 401 errors caused by stale placeholder values.

---

## Standard Workflow

```bash
# 1. Install
pip install azuredevops-github-migration

# 2. Initialize config & .env template
azuredevops-github-migration init --template full   # or jira-users

# 3. Edit .env (tokens + org names) & config.json

# 4. Run diagnostics (optional but recommended)
azuredevops-github-migration doctor

# 5. Analyze and create plan
azuredevops-github-migration analyze --create-plan

# 6. Dry run one repo
azuredevops-github-migration migrate --project P --repo R --dry-run

# 7. Freeze source repos (enterprise)
azuredevops-github-migration freeze --plan migration_plan.json --config config.json --state-file state.json

# 8. Migrate (single or batch)
azuredevops-github-migration migrate --project P --repo R
azuredevops-github-migration batch --plan migration_plan.json --config config.json --state-file state.json --concurrency 4

# 9. Monitor progress
azuredevops-github-migration status --state-file state.json

# 10. Verify migration
azuredevops-github-migration verify --state-file state.json --config config.json

# 11. Unfreeze source repos
azuredevops-github-migration unfreeze --plan migration_plan.json --config config.json --state-file state.json
```

### Enterprise Migration (700+ Repos)

For large-scale migrations, use the full enterprise lifecycle with freeze, batch, state tracking, and verification. See the [Enterprise Demo Walkthrough](docs/user-guide/ENTERPRISE_DEMO_WALKTHROUGH.md) for a complete step-by-step guide.

```
Analyze --> Plan --> Dry Run --> Freeze --> Batch Migrate --> Monitor --> Retry --> Verify --> Unfreeze
```

Key enterprise flags for `batch`:

| Flag | Purpose |
|------|---------|
| `--concurrency N` | Parallel migration threads (default: 4) |
| `--state-file F` | State file for resume/retry tracking |
| `--wave NAME` | Wave label in state file |
| `--retry-failed` | Re-attempt only failed repos |
| `--dry-run` | Simulate without changes |

---

## Commands Overview

| Command | Purpose | Typical Use |
|---------|---------|-------------|
| `init` | Create config & .env template | First run |
| `quickstart` | Guided wizard (init + doctor + analyze) | First run |
| `analyze` | Inventory org/project & create plan | Planning |
| `migrate` | Migrate a single repository | Iterative testing / final run |
| `batch` | Execute plan for multiple repos | Wave migrations |
| `freeze` | Lock ADO repos (deny push via Security API) | Pre-migration |
| `unfreeze` | Restore ADO repo permissions from state | Post-migration |
| `status` | Migration progress dashboard | Monitoring |
| `verify` | Branch parity verification | Post-migration |
| `doctor` | Environment & readiness diagnostics | Pre-flight |
| `update-env` | PowerShell loader for `.env` | Windows onboarding |
| `interactive` | Arrow-key menu wrapper | New users |

### `migrate` - Single Repository Migration

```bash
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --github-repo "new-name" --config config.json
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-issues --config config.json
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --pipelines-scope repository --exclude-disabled-pipelines --verify-remote --config config.json
```

### `analyze` - Organization Analyzer

```bash
azuredevops-github-migration analyze --create-plan --config config.json
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items
azuredevops-github-migration analyze --format csv --config config.json
```

### `batch` - Batch Migration

```bash
azuredevops-github-migration batch --create-sample
azuredevops-github-migration batch --dry-run --plan migration_plan.json --config config.json
azuredevops-github-migration batch --plan migration_plan.json --config config.json --state-file state.json --concurrency 4 --wave wave-1
azuredevops-github-migration batch --plan migration_plan.json --config config.json --state-file state.json --retry-failed
```

### `freeze` / `unfreeze` - ADO Repo Locking

```bash
azuredevops-github-migration freeze --plan migration_plan.json --config config.json --state-file state.json
azuredevops-github-migration unfreeze --plan migration_plan.json --config config.json --state-file state.json
```

### `status` - Migration Dashboard

```bash
azuredevops-github-migration status --state-file state.json
azuredevops-github-migration status --state-file state.json --show-errors
```

### `verify` - Post-Migration Verification

```bash
azuredevops-github-migration verify --state-file state.json --config config.json
```

### Jira Mode (Skip Work Items)

If you manage issues in Jira, suppress work item processing:

```bash
azuredevops-github-migration init --template jira-users
azuredevops-github-migration analyze --project "MyProject" --create-plan --config config.json --skip-work-items
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --config config.json
azuredevops-github-migration batch --plan migration_plan.json --config config.json
```

Notes:
* `--skip-work-items` avoids Work Item API calls and removes work item fields from the plan.
* In batch mode: if a plan omits `migrate_issues`, the tool defaults those entries to `False`.
* In single migrations: if your config has `"migrate_work_items": false`, issues are auto-disabled.

### Alternative Commands (Development/Source)

```bash
python -m azuredevops_github_migration --help
python -m azuredevops_github_migration.migrate --project "MyProject" --repo "my-repo" --config config.json
python -m azuredevops_github_migration.analyze --create-plan --config config.json
python -m azuredevops_github_migration.batch_migrate --plan migration_plan.json --config config.json
```

### Standalone Entry Points

| Short command | Maps to |
|---------------|---------|
| `ado2gh-migrate` | `azuredevops-github-migration migrate` |
| `ado2gh-analyze` | `azuredevops-github-migration analyze` |
| `ado2gh-batch` | `azuredevops-github-migration batch` |
| `ado2gh-doctor` | `azuredevops-github-migration doctor` |
| `ado2gh-status` | `azuredevops-github-migration status` |
| `ado2gh-freeze` | `azuredevops-github-migration freeze` |
| `ado2gh-unfreeze` | `azuredevops-github-migration unfreeze` |
| `ado2gh-verify` | `azuredevops-github-migration verify` |

---

## Key CLI Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--dry-run` | Simulate migration without side effects | off |
| `--no-issues` | Skip work item to issue conversion | off |
| `--no-pipelines` | Skip pipeline conversion | off |
| `--no-git` | Skip Git history migration | off |
| `--pipelines-scope {project\|repository}` | Control pipeline selection scope | project |
| `--exclude-disabled-pipelines` | Omit disabled/paused pipelines | off |
| `--verify-remote` | Compare remote branch list to local after push | off |
| `--skip-work-items` (analyze) | Do not query work items; omit related fields | off |
| `--concurrency N` (batch) | Parallel migration threads | 4 |
| `--state-file F` (batch/freeze) | State file for resume/retry tracking | auto |
| `--wave NAME` (batch) | Wave label in state file | default |
| `--retry-failed` (batch) | Re-attempt only failed repos | off |
| `--show-errors` (status) | Show error details for failed repos | off |
| `--debug` | Verbose logging | off |
| `--validate-only` | Validate config & credentials only | off |

Automatic behaviors:
* If config contains `"migrate_work_items": false`, single repo migrations suppress issues without needing `--no-issues`.
* If a migration plan omits `migrate_issues` (produced via `--skip-work-items`), batch migration treats all entries as code-only.

---

## Interactive Menu

Launch an arrow-key driven menu for common actions:

```bash
azuredevops-github-migration interactive
```

The menu hides the "Init" option automatically once both `config.json` and `.env` are present. Force it to always appear by setting `MIGRATION_SHOW_INIT_ALWAYS=1`.

### Analyze Scope Selector

Selecting "Analyze organization" presents a scope choice:
1. **Single project** (faster) -- prompts with paginated fuzzy-search project picker.
2. **Full organization** -- walks all projects & repositories.

### Migrate Wizard

Selecting "Migrate repository" launches an inline wizard:
1. Project picker (paginated + fuzzy + jump-to-letter)
2. Repository picker (within selected project)
3. Mode selection: Dry run vs Real migration
4. Optional custom GitHub repository name

### Readiness Banner

A one-line readiness banner summarizes environment state on launch:

```
=== Environment Readiness: READY ===
Status: PAT=OK TOKEN=OK ADO_ORG=OK GH_ORG=OK
```

Legend: OK = present & not a placeholder, PH = placeholder value, MISSING = not set. Disable with `MIGRATION_NO_BANNER=1`.

### Project List Navigation

When you have many Azure DevOps projects (100+), the project picker provides:

| Feature | How to Use |
|---------|------------|
| Pagination | Next page / Prev page entries (10 per page) |
| Search / filter | Substring or fuzzy subsequence matching (case-insensitive) |
| Jump to letter | Jump to first project starting with a character |
| Clear filter | Restore full project list |
| Skip | Launch full interactive menu immediately |
| Cancel | Press Esc or pick Cancel selection |

### Automatic Work Item Skipping in Jira Mode

If you initialized with the `jira-users` template (which sets `"migration": {"migrate_work_items": false}`), the interactive Analyze path automatically injects `--skip-work-items`.

---

## Configuration

### Environment Variables

Create a `.env` file (never commit real secrets):

```
AZURE_DEVOPS_PAT=xxxx
GITHUB_TOKEN=ghp_xxxx
AZURE_DEVOPS_ORGANIZATION=your-ado-org   # alias: AZURE_DEVOPS_ORG
GITHUB_ORGANIZATION=your-gh-org         # alias: GITHUB_ORG
```

If both a canonical name and an alias are set, the canonical name wins. The tool auto-loads `.env` on every command without overwriting existing shell variables.

Use `doctor --fix-env` to append missing canonical variables without touching existing values.

Security & version control:
* `.env` is git-ignored. Never commit real tokens; rotate immediately if exposed.
* CI/CD should inject secrets via environment or secrets manager.

### Config File

Edit `config.json` to configure:

```json
{
    "azure_devops": {"organization": "${AZURE_DEVOPS_ORGANIZATION}", "project": "MyProject"},
    "github": {"organization": "${GITHUB_ORGANIZATION}", "create_private_repos": true},
    "migration": {"migrate_work_items": false, "migrate_pipelines": true}
}
```

See the [Configuration Reference](docs/technical/configuration.md) for complete options.

### Repository Name Normalization

If your Azure DevOps repository name contains whitespace (e.g. `"My Repo"`), the migration automatically converts spaces to underscores (`My_Repo`) unless you provide `--github-repo`.

### Workflow Filename Normalization (Pipelines to GitHub Actions)

Pipeline names are converted into workflow filenames:

| Example Pipeline Name | Workflow Filename |
|-----------------------|-------------------|
| `Build & Test`        | `build-test.yml`  |
| `CI/CD (Prod)`        | `ci-cd-prod.yml`  |
| `Deploy` (duplicate)  | `deploy.yml`, `deploy-2.yml` |

Optional configuration in `config.json`:

```jsonc
{
  "naming": {
    "workflow": {"separator": "-", "lowercase": true, "max_length": 50},
    "repository": {"whitespace_strategy": "underscore", "force_lowercase": false}
  }
}
```

---

## Diagnostics (`doctor`)

Run a fast, side-effect-free health check at any time:

```bash
azuredevops-github-migration doctor                     # Human formatted
azuredevops-github-migration doctor --json              # Machine readable
azuredevops-github-migration doctor --fix-env            # Append missing env placeholders
azuredevops-github-migration doctor --edit-env           # Safe interactive .env editor
azuredevops-github-migration doctor --assist             # Diagnostics then remediation submenu
azuredevops-github-migration doctor --fix-env --assist   # Placeholders + remediation
azuredevops-github-migration doctor --edit-env --assist  # Editor then remediation submenu
azuredevops-github-migration doctor --skip-network       # Skip network reachability checks
```

What it checks:
* Python interpreter & package importability
* Git presence & version
* Config file exists and parses
* Network reachability (api.github.com & dev.azure.com TCP 443)
* Required environment variables (AZURE_DEVOPS_PAT, GITHUB_TOKEN, AZURE_DEVOPS_ORGANIZATION, GITHUB_ORGANIZATION)

Secrets are masked (first 4 ... last 4). Exit codes: 0 = all passed, 1 = critical failures.

### Doctor Composite Modes (Deprecated)

`--doctor-mode` shortcuts still work for backward compatibility but will be removed in a future major release. Prefer explicit flags:

```bash
# Old:  doctor --doctor-mode fix-assist
# New:  doctor --fix-env --assist
```

### Interactive .env Editor

```bash
azuredevops-github-migration doctor --edit-env
```

* Prompts for each canonical variable; press Enter to keep existing
* Existing values shown masked
* File ordering & comments preserved; missing keys appended
* Timestamped backup (`.env.bak.YYYYmmddHHMMSS`) created before any write
* Diagnostics re-run after saving

| Command | Purpose | Writes to `.env` | Requires PowerShell |
|---------|---------|------------------|---------------------|
| `update-env` | Load & audit env via PowerShell script | No | Yes |
| `doctor --edit-env` | Edit & persist vars in pure Python | Yes | No |

---

## PowerShell Helper (Windows)

The PowerShell helper (`scripts/Test-MigrationEnv.ps1`) complements `doctor` with interactive and scriptable environment audit:

```powershell
./scripts/Test-MigrationEnv.ps1                    # Basic audit (auto-prompts if missing)
./scripts/Test-MigrationEnv.ps1 -Prompt            # Force interactive entry
./scripts/Test-MigrationEnv.ps1 -Load -Prompt      # Load from .env then prompt for missing
./scripts/Test-MigrationEnv.ps1 -Load -Overwrite   # Overwrite session values from .env
./scripts/Test-MigrationEnv.ps1 -Json              # JSON output for pipelines
./scripts/Test-MigrationEnv.ps1 -Load -FailOnMissing -Json  # Fail if anything missing
```

Exit codes: 0 = ran successfully, 2 = `-FailOnMissing` and at least one variable absent.

---

## Migration Scope

### What Gets Migrated

| Category | Migrated | Notes |
|----------|----------|-------|
| Git history | Yes | Branches, tags, commits |
| Pipelines | Yes | Converted to GitHub Actions (no local YAML writes by default) |
| Work items to Issues | Optional | Map fields & states; HTML to Markdown |

### What Doesn't Get Migrated

* Pull requests (GitHub API doesn't support creating historical PRs)
* Branch policies, code review comments
* Wiki pages, test plans, boards configuration
* Extensions, customizations, work item attachments
* Build/Release pipeline history (only YAML definitions are converted)

---

## Post-Migration Verification

### CLI Verification (v3.0.0)

```bash
azuredevops-github-migration verify --state-file state.json --config config.json
```

Compares branches between ADO source and GitHub target via `git ls-remote --heads`.

### PowerShell Verification

```powershell
./scripts/verify-migration.ps1 -Org myorg -Repo myrepo
./scripts/verify-migration.ps1 -Org myorg -Repo myrepo -Json | ConvertFrom-Json
```

Exit codes: 0 = all good, 2 = warnings, 3 = fatal.

Advanced capabilities:

| Feature | Parameters | Description |
|---------|------------|-------------|
| Branch Protection | `-CheckBranchProtection -BranchProtectionBranches main,release/*` | Verifies branches have protection enabled |
| Tag Parity | `-ExpectedTagCount 42` or auto-detected | Compares tag count against expected |
| Workflow Lint | `-LintWorkflows` | Structural lint: `on:` and `jobs:` blocks, merge conflict markers |
| Exit Control | `-FailOnBranchProtection -FailOnLintErrors -FailOnTagMismatch` | Promote discrepancies to fatal errors |
| Summary File | `-SummaryFile verification-summary.json` | Write full JSON to static file |

See `docs/user-guide/POST_MIGRATION_CHECKLIST.md` for detailed validation steps.

### GitHub Action Automation

An example reusable workflow (`examples/verify-migration-workflow.yml`) is provided -- copy it into the **target migrated repository** as `.github/workflows/verify-migration.yml` for automated verification. Do **not** add converted pipeline workflows to the tool repo; they belong only in destination repos.

---

## Authentication

Use least privilege. Start with minimum scopes and add only if needed.

### Azure DevOps PAT

Minimum (repository migration only):
- Code: Read (clone repositories, enumerate branches/tags)
- Project and Team: Read (list projects & repos)

Add ONLY if needed:
- Work Items: Read (when converting work items to GitHub issues)
- Security: Manage (required for `freeze` / `unfreeze` commands)

### GitHub PAT

Minimum:
- `repo` (covers contents, issues, pulls for private & public repos)

Add ONLY if needed:
- `admin:org` (tool needs to create new repositories inside an organization)
- `delete_repo` (rollback that deletes created repos)
- `workflow` (programmatically manipulate Actions runs)

### Scenario Scope Matrix

| Scenario | Azure DevOps Scopes | GitHub Scopes |
|----------|---------------------|---------------|
| Single repo, no issues | Code (Read), Project & Team (Read) | repo |
| Repo + work items | Code (Read), Project & Team (Read), Work Items (Read) | repo |
| Batch migrate | Code (Read), Project & Team (Read) | repo |
| Auto create org repos | Code (Read), Project & Team (Read) | repo, admin:org |
| Freeze/unfreeze repos | Code (Read), Project & Team (Read), Security (Manage) | repo |

### Obtaining Tokens

**Azure DevOps:** Avatar (top-right) > User settings > Personal access tokens > New Token. Select Custom defined scopes, choose only what you need. Copy immediately; cannot be recovered later.

**GitHub (Fine-grained PAT, recommended):** Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token. Set short expiration. Under Repository permissions: Contents (Read and write), Metadata (Read), Issues (Read & write if migrating work items).

**GitHub (Classic PAT):** Settings > Developer settings > Personal access tokens > Tokens (classic) > Generate new token. Select `repo` scope. Add `admin:org` only if creating repos in an org.

Prefer fine-grained tokens; use classic only when composite scopes are needed.

### Environment Variable Setup

PowerShell:
```powershell
$env:AZURE_DEVOPS_PAT = 'xxxxxxxxxxxxxxxxxxxxxxxx'
$env:GITHUB_TOKEN = 'ghp_xxxxxxxxxxxxxxxxxxxxx'
```

bash/zsh:
```bash
export AZURE_DEVOPS_PAT=xxxxxxxxxxxxxxxxxxxxxxxx
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
```

---

## Project Structure

```
azuredevops-github-migration/
├── README.md
├── pyproject.toml                         # Build configuration & entry points
├── CHANGELOG.md
│
├── src/azuredevops_github_migration/      # Python package
│   ├── __init__.py                        # Package init, version, lazy imports
│   ├── __main__.py                        # python -m entry point
│   ├── cli.py                             # Unified CLI dispatcher
│   ├── migrate.py                         # Single-repo migration orchestrator
│   ├── analyze.py                         # Organization analysis & planning
│   ├── batch_migrate.py                   # Batch migration with concurrency & state
│   ├── freeze.py                          # ADO repo freeze/unfreeze via Security API
│   ├── freeze_cli.py                      # Freeze/unfreeze CLI wrappers
│   ├── status.py                          # Migration status dashboard
│   ├── verify.py                          # Post-migration branch verification
│   ├── state.py                           # Thread-safe JSON state persistence
│   ├── config.py                          # Configuration loading & validation
│   ├── exceptions.py                      # Custom exception classes
│   ├── naming.py                          # Repository & workflow name normalization
│   ├── doctor.py                          # Environment diagnostics
│   ├── interactive.py                     # Arrow-key interactive menu
│   ├── init.py                            # Config file initialization
│   ├── quickstart.py                      # Guided quickstart wizard
│   └── utils.py                           # Shared utilities (HTML conversion, rate limiting)
│
├── examples/
│   ├── jira-users-config.json             # Config for Jira users (most common)
│   ├── full-migration-config.json         # Complete migration config
│   ├── sample-migration-plan.json         # Batch migration plan template
│   └── verify-migration-workflow.yml      # GitHub Actions verification workflow
│
├── scripts/
│   ├── setup.sh                           # Automated setup (Linux/macOS)
│   ├── setup.ps1                          # Automated setup (Windows)
│   ├── Test-MigrationEnv.ps1              # PowerShell environment audit
│   └── verify-migration.ps1              # Post-migration verification script
│
├── tests/                                 # 30+ test modules (pytest)
│
└── docs/
    ├── user-guide/
    │   ├── HOW_TO_GUIDE.md                # Step-by-step instructions
    │   ├── ENTERPRISE_DEMO_WALKTHROUGH.md # Enterprise migration guide
    │   ├── PRE_MIGRATION_CHECKLIST.md     # 100+ item pre-migration checklist
    │   ├── POST_MIGRATION_CHECKLIST.md    # Post-migration validation
    │   └── TESTING.md                     # Testing procedures
    └── technical/
        ├── api.md                         # API reference
        ├── configuration.md               # Configuration guide
        └── troubleshooting.md             # Problem resolution
```

---

## Logging and Reports

* Console output with progress indicators
* Detailed log file: `migration.log`
* JSON reports with complete migration data, statistics, and success/failure tracking
* When `--verify-remote` is used, logs include remote vs local branch comparison

---

## Documentation

| Guide | Link |
|-------|------|
| How-To Guide | [docs/user-guide/HOW_TO_GUIDE.md](docs/user-guide/HOW_TO_GUIDE.md) |
| Enterprise Demo Walkthrough | [docs/user-guide/ENTERPRISE_DEMO_WALKTHROUGH.md](docs/user-guide/ENTERPRISE_DEMO_WALKTHROUGH.md) |
| Pre-Migration Checklist | [docs/user-guide/PRE_MIGRATION_CHECKLIST.md](docs/user-guide/PRE_MIGRATION_CHECKLIST.md) |
| Post-Migration Checklist | [docs/user-guide/POST_MIGRATION_CHECKLIST.md](docs/user-guide/POST_MIGRATION_CHECKLIST.md) |
| Testing Guide | [docs/user-guide/TESTING.md](docs/user-guide/TESTING.md) |
| Configuration Reference | [docs/technical/configuration.md](docs/technical/configuration.md) |
| Troubleshooting | [docs/technical/troubleshooting.md](docs/technical/troubleshooting.md) |
| API Documentation | [docs/technical/api.md](docs/technical/api.md) |

### Ready-to-Use Examples

* [examples/jira-users-config.json](examples/jira-users-config.json) -- Optimized for Jira users (most common)
* [examples/full-migration-config.json](examples/full-migration-config.json) -- Complete migration with work items
* [examples/sample-migration-plan.json](examples/sample-migration-plan.json) -- Batch migration template

---

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Authentication errors | Verify PATs, check scopes, ensure tokens haven't expired |
| Missing PAT / tokens | `doctor --fix-env` then fill placeholders |
| Git not found | Install Git & ensure PATH |
| Network unreachable | Check firewall/proxy; retry `doctor` |
| Permission errors | Re-check PAT scopes; narrow to minimum needed |
| Rate limiting | Adjust `delay_between_requests` in config |
| Large repos slow | Migrate during off-peak hours; monitor disk space |
| Work item conversion issues | Complex HTML may need manual review; custom fields not migrated |
| `403` on freeze/unfreeze | PAT missing Security (Manage) scope |
| Batch exits with code 1 | Run `status --show-errors`, then `batch --retry-failed` |

---

## Limitations

* Very large repositories (>5GB) may take significant time
* Both Azure DevOps and GitHub have API rate limits
* Some metadata may be lost in translation
* Azure DevOps custom fields require manual mapping
* Work item attachments are not migrated automatically
* Pull requests and code review comments cannot be migrated

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

* Never commit personal access tokens
* Use environment variables for sensitive configuration
* Review migration reports before sharing
* Consider using service accounts for production migrations
* Rotate tokens immediately if exposed
