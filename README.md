# Azure DevOps → GitHub Migration Tool

Production‑ready CLI to migrate Azure DevOps repositories (and optionally work items & pipelines) to GitHub with safety, repeatability, and clear diagnostics.

> Need a fast Jira‑mode (code + pipelines only)? See Quick Start below.

---

## ✨ Key Features
| Area | Capability |
|------|------------|
| Repositories | Full Git history (branches, tags, metadata) |
| Pipelines | Azure DevOps pipelines → GitHub Actions (temp directory, never written locally unless allowed) |
| Work Items (optional) | Map to GitHub issues (HTML → Markdown, type/state/priority to labels) |
| Batch Mode | Plan‑driven multi‑repo execution |
| Analysis | Inventory & migration planning report |
| Diagnostics | `doctor`, placeholder auto‑append, interactive remediation & editor |
| Interactive UX | Arrow‑key menu (`interactive`) + PowerShell env loader (`update-env`) |
| Safety | Dry runs, rate limiting, retry logic, masked tokens |
| Reporting | JSON migration reports + verification script integration |
| Extensibility | Clean Python package layout, tests, semantic versioning |

---

## 🚀 Quick Start (Jira Users – No Work Items)
```bash
pip install azuredevops-github-migration
cp examples/jira-users-config.json config.json
azuredevops-github-migration analyze --project "MyProject" --create-plan --skip-work-items
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo"
azuredevops-github-migration batch --plan migration_plan_<org>_*.json
```

## ⚙️ Standard Workflow
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

# 7. Migrate (single or batch)
azuredevops-github-migration migrate --project P --repo R
azuredevops-github-migration batch --plan migration_plan_<org>_*.json

# 8. Verify & archive source
./scripts/verify-migration.ps1 -Org <org> -Repo <repo> -Json | ConvertFrom-Json
```

---

## 🧪 Commands Overview
| Command | Purpose | Typical Use |
|---------|---------|-------------|
| `init` | Create config & .env template | First run |
| `analyze` | Inventory org / project & create plan | Planning |
| `migrate` | Migrate a single repository | Iterative testing / final run |
| `batch` | Execute plan for multiple repos | Wave migrations |
| `doctor` | Environment & readiness diagnostics | Pre-flight |
| `update-env` | PowerShell loader for `.env` | Windows onboarding |
| `interactive` | Arrow‑key menu wrapper | New users |

### Doctor Composite Modes
Use `--doctor-mode` for quick combinations:

| Mode | Expands To | Description |
|------|------------|-------------|
| `plain` | diagnostics | Human / JSON diagnostics only |
| `fix` | `--fix-env` | Append missing canonical env placeholders |
| `assist` | `--assist` | Open remediation submenu |
| `fix-assist` | `--fix-env --assist` | Append placeholders then assist |
| `edit` | `--edit-env` | Safe interactive .env editor (with backup) |
| `edit-assist` | `--edit-env --assist` | Edit then remediation submenu |

Examples:
```bash
azuredevops-github-migration doctor --doctor-mode fix-assist
azuredevops-github-migration doctor --doctor-mode edit --json   # (note: edit & json cannot combine; omit --json here)
```

---

## 🖥️ Interactive Menu (Demo)

Placeholder (replace after recording):

[![Interactive Menu Demo](https://asciinema.org/a/PLACEHOLDER.svg)](https://asciinema.org/a/PLACEHOLDER)

Or embed a GIF:
`docs/media/interactive-menu.gif`

Record instructions (developer machine):
```bash
pip install asciinema
asciinema rec -c "azuredevops-github-migration interactive" interactive.cast
# After recording: press Ctrl+D, then upload
asciinema upload interactive.cast
```

---

## 🔐 Configuration Essentials
`.env` (never commit real secrets):
```
AZURE_DEVOPS_PAT=xxxx
GITHUB_TOKEN=ghp_xxxx
AZURE_DEVOPS_ORGANIZATION=your-ado-org   # alias: AZURE_DEVOPS_ORG
GITHUB_ORGANIZATION=your-gh-org         # alias: GITHUB_ORG
```
`config.json` (example excerpt):
```json
{
    "azure_devops": {"organization": "${AZURE_DEVOPS_ORGANIZATION}", "project": "MyProject"},
    "github": {"organization": "${GITHUB_ORGANIZATION}", "create_private_repos": true},
    "migration": {"migrate_work_items": false, "migrate_pipelines": true}
}
```
Use `doctor --fix-env` to append any missing canonical variables without touching existing values.

---

## 📦 Migration Scope
| Category | Migrated | Notes |
|----------|----------|-------|
| Git history | ✅ | Branches, tags, commits |
| Pipelines | ✅ | Converted to GitHub Actions (guardrail: no local YAML writes by default) |
| Work items → Issues | ✅ (optional) | Map fields & states; HTML → Markdown |
| Attachments / PRs / Wiki / Test Plans | ❌ | Not in scope |
| Branch policies | ❌ | Recreate manually |
| Security tokens in logs | ❌ | Masked / never printed |

---

## 🧭 Example: Full (Non‑Jira) Flow
```bash
azuredevops-github-migration init --template full
azuredevops-github-migration doctor --doctor-mode fix
azuredevops-github-migration analyze --create-plan
azuredevops-github-migration migrate --project AppSuite --repo core-api --dry-run
azuredevops-github-migration migrate --project AppSuite --repo core-api
azuredevops-github-migration batch --plan migration_plan_<org>_*.json
./scripts/verify-migration.ps1 -Org <org> -Repo core-api -Json | ConvertFrom-Json
```

## 🧭 Example: Jira Mode (Code + Pipelines only)
```bash
azuredevops-github-migration init --template jira-users
azuredevops-github-migration analyze --project Legacy --create-plan --skip-work-items
azuredevops-github-migration migrate --project Legacy --repo ui --dry-run
azuredevops-github-migration migrate --project Legacy --repo ui
```

---

## 🔍 Verification (Post‑Migration)
```powershell
./scripts/verify-migration.ps1 -Org <org> -Repo <repo> -Json | ConvertFrom-Json
```
Checks branches, tags, workflow presence, placeholder statistics. Add flags for lint / branch protection as needed.

---

## 🛠 Key Flags (Selected)
| Flag | Purpose |
|------|---------|
| `--dry-run` | Simulate migration, no pushes |
| `--no-issues` | Suppress work item → issue conversion |
| `--skip-work-items` (analyze) | Omit work item queries & exclude issue logic |
| `--pipelines-scope repository` | Limit pipelines to repo only |
| `--exclude-disabled-pipelines` | Skip paused pipelines |
| `--verify-remote` | Compare pushed vs local branches |
| `--fix-env` | Append missing env placeholders |
| `--doctor-mode <mode>` | Composite diagnostic shortcuts |

---

## 📚 Documentation
| Audience | Resource |
|----------|----------|
| Step‑by‑step | `docs/user-guide/HOW_TO_GUIDE.md` |
| Checklist | `docs/user-guide/PRE_MIGRATION_CHECKLIST.md` |
| Testing | `docs/user-guide/TESTING.md` |
| Config reference | `docs/technical/configuration.md` |
| Troubleshooting | `docs/technical/troubleshooting.md` |
| API internals | `docs/technical/api.md` |

---

## 🤖 Recording a Demo (Optional)
1. `asciinema rec -c "azuredevops-github-migration interactive" interactive.cast`
2. Navigate menu (Doctor diagnostics, Init, Analyze, Migrate)
3. Ctrl+D to finish → upload → replace PLACEHOLDER link above
4. (Optional) Convert to GIF with `agg`: `agg interactive.cast interactive-menu.gif`

---

## 🤝 Contributing
Pull requests welcome: keep changes focused, add/adjust tests, update CHANGELOG if user-facing.

## 📄 License
MIT © Stewart Burton

---

<sub>For security: never commit real tokens. Rotate immediately if exposed. Use fine‑grained GitHub PATs & minimal Azure DevOps scopes.</sub>


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
    - Guardrail: The tool no longer writes converted workflow YAML into its own repository. Files are generated in a temp directory and pushed directly to the target repo. Use `--allow-local-workflows` only if you intentionally want local emission (not recommended).
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
- **Interactive Menu (New)**: Launch an arrow-key driven menu with `azuredevops-github-migration interactive` for common tasks
- **Environment Loader (New)**: Use `azuredevops-github-migration update-env` to invoke the PowerShell helper and load variables from `.env`
- **Doctor Assist (New)**: Use `azuredevops-github-migration doctor --assist` for an interactive remediation submenu (run PowerShell loader, append placeholders, re-run diagnostics)
- **.env Editor (New)**: Use `azuredevops-github-migration doctor --edit-env` to interactively edit & persist required environment variables with automatic timestamped backup
- **Doctor Mode Shortcuts (New)**: Use `--doctor-mode <plain|fix|assist|fix-assist|edit|edit-assist>` for fast non-interactive combinations (see Doctor section)

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

# (New) Run diagnostics / environment health check
azuredevops-github-migration doctor --config config.json
# or JSON output
azuredevops-github-migration doctor --json

# (New) Composite doctor modes (maps to existing flags)
azuredevops-github-migration doctor --doctor-mode plain          # == diagnostics only
azuredevops-github-migration doctor --doctor-mode fix            # == --fix-env
azuredevops-github-migration doctor --doctor-mode assist         # == --assist
azuredevops-github-migration doctor --doctor-mode fix-assist     # == --fix-env --assist
azuredevops-github-migration doctor --doctor-mode edit           # == --edit-env
azuredevops-github-migration doctor --doctor-mode edit-assist    # == --edit-env --assist

# (New) Update / load environment variables from .env via PowerShell script
azuredevops-github-migration update-env

# (New) Launch interactive arrow-key menu (requires optional dependency `questionary`)
azuredevops-github-migration interactive

# (New) Interactive .env editor (creates backup then re-runs diagnostics)
azuredevops-github-migration doctor --edit-env

# 2. Analyze your organization (optional)
azuredevops-github-migration analyze --create-plan  # --config no longer required when using default config.json

# 3. Test migration (safe, no changes)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --dry-run --config config.json

# 4. Actual migration (Jira users - most common)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-issues --config config.json

# Skip Git history (create target repo + optionally pipelines/issues only)
azuredevops-github-migration migrate --project "MyProject" --repo "my-repo" --no-git --config config.json

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
 * `--no-git` skips mirror cloning/pushing; useful for testing pipeline or issue conversion only.
 * `doctor` command helps diagnose path/import, git availability, network reachability, and token presence.

## Configuration

### Environment Variables

Create a `.env` file with your authentication tokens:

```bash
AZURE_DEVOPS_PAT=your_azure_devops_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

You may also specify organization names (recommended) so commands and the diagnostic tool can resolve them without prompting:

```
AZURE_DEVOPS_ORGANIZATION=your-azure-devops-org   # alias: AZURE_DEVOPS_ORG
GITHUB_ORGANIZATION=your-github-org              # alias: GITHUB_ORG
```

If both a canonical name and an alias are set the canonical name wins. The tool will attempt to load the `.env` file automatically for every command (without overwriting variables already set in your shell session).

Important – template change (Sept 2025):
* Earlier versions of this project shipped a minimal `.env` template containing only `AZURE_DEVOPS_PAT` and `GITHUB_TOKEN`.
* The template now (and all future `init` runs) includes the two organization variables: `AZURE_DEVOPS_ORGANIZATION` and `GITHUB_ORGANIZATION`.
* If your existing `.env` predates this change you can simply add those two lines manually (recommended) OR run:
    * `azuredevops-github-migration doctor --fix-env` – this will append placeholder lines for any missing canonical variables without modifying existing secrets.
* Aliases (`AZURE_DEVOPS_ORG`, `GITHUB_ORG`) still work for backward compatibility, but the canonical names are preferred and are what new docs & diagnostics display.

Security & version control:
* `.env` is intentionally git‑ignored (see `.gitignore`).
* To change the default template for new contributors, edit `.env.example` – not someone’s personal `.env`.
* Never commit real tokens; rotate immediately if you do.
* CI/CD should inject secrets via environment or secrets manager, not by committing a `.env` file.

### Pre‑Flight Diagnostics & Environment Audit (`doctor`)

Run a fast, side‑effect‑free health check at any time. You can either compose flags manually or use the new `--doctor-mode` composite flag:

```bash
azuredevops-github-migration doctor                     # Human formatted (plain mode)
azuredevops-github-migration doctor --json              # Machine readable

# Composite shortcut examples:
azuredevops-github-migration doctor --doctor-mode fix          # Append missing placeholders then diagnostics
azuredevops-github-migration doctor --doctor-mode assist       # Diagnostics then remediation submenu
azuredevops-github-migration doctor --doctor-mode fix-assist   # Placeholders + remediation
azuredevops-github-migration doctor --doctor-mode edit         # Safe interactive .env editor
azuredevops-github-migration doctor --doctor-mode edit-assist  # Editor then remediation submenu
```

What it checks:
* Python interpreter & package importability
* Git presence & version
* Config file exists and parses (`--config` to point at a different file; default `config.json`)
* Network reachability (api.github.com & dev.azure.com TCP 443)
* Required environment variables & accepted aliases:
    - AZURE_DEVOPS_PAT
    - GITHUB_TOKEN
    - AZURE_DEVOPS_ORGANIZATION (alias: AZURE_DEVOPS_ORG)
    - GITHUB_ORGANIZATION (alias: GITHUB_ORG)

Secrets are masked (first 4 … last 4) or replaced with `****` for short values. The command auto‑loads a local `.env` (if present) before auditing so you don't need to export variables manually. It never overwrites values already present in the process environment.

Exit codes:
* 0 = All critical checks passed
* 1 = One or more critical failures (missing PAT/TOKEN, git missing, or package cannot be imported)

Example JSON excerpt:
```json
{
    "env": {
        "variables": {
            "AZURE_DEVOPS_PAT": {"present": true, "masked": "abcd...wxyz"},
            "GITHUB_TOKEN": {"present": true, "masked": "abcd...wxyz"}
        },
        "all_present": true
    }
}
```

### PowerShell Helper (Windows) – `scripts/Test-MigrationEnv.ps1`

The PowerShell helper provides an interactive and scriptable environment audit. It complements (but does not replace) the `doctor` command.

Core capabilities:
- Reads a `.env` file (defaults to `./.env`) and inspects four required values
    - `AZURE_DEVOPS_PAT`
    - `GITHUB_TOKEN`
    - `AZURE_DEVOPS_ORGANIZATION` (alias: `AZURE_DEVOPS_ORG`)
    - `GITHUB_ORGANIZATION` (alias: `GITHUB_ORG`)
- Optional load of values into the current PowerShell session (`-Load`) without overwriting existing values unless `-Overwrite` is also supplied
- Optional interactive prompting (`-Prompt`) – secure input for tokens, plain input for organization names
- Automatic prompting if required variables are missing and neither `-Json` nor `-Prompt` was specified (so a plain run helps you fill gaps)
- JSON machine output (`-Json`) suitable for pipeline gating
- Masked display (first 4 + last 4 chars; short values become `****`)

Table column meanings:
| Column | Meaning |
|--------|---------|
| `Name` | Canonical variable name |
| `InFile` | Present in `.env` (or alias present) |
| `InSession` | Present in current PowerShell process environment |
| `FileMasked` | Masked value sourced from file (if present) |
| `SessionMasked` | Masked in‑session value (if present) |
| `Matches` | Simply indicates the variable is present both in file AND session (does not compare literal equality) |

Usage examples:
```powershell
# Basic audit (will auto‑prompt if something is missing)
./scripts/Test-MigrationEnv.ps1

# Force interactive entry even if everything is already set
./scripts/Test-MigrationEnv.ps1 -Prompt

# Load from .env (without overwriting existing session values) then prompt for any still missing
./scripts/Test-MigrationEnv.ps1 -Load -Prompt

# Overwrite existing session values from the .env file
./scripts/Test-MigrationEnv.ps1 -Load -Overwrite

# JSON output for pipelines (never prompts automatically in JSON mode)
./scripts/Test-MigrationEnv.ps1 -Json | ConvertFrom-Json

# Fail the build (exit code 2) if anything is missing after attempted load
./scripts/Test-MigrationEnv.ps1 -Load -FailOnMissing -Json

# Quiet mode suppresses table & summary (but will still auto‑prompt if variables are missing)
./scripts/Test-MigrationEnv.ps1 -Quiet
```

Exit codes (current script implementation):
| Code | Meaning |
|------|---------|
| 0 | Ran successfully (even if values are missing and `-FailOnMissing` was NOT supplied) |
| 2 | `-FailOnMissing` specified AND at least one required variable absent from the session after load / prompt |

Notes:
- There is intentionally no distinct "fatal vs warning" code split (older documentation referenced 1/2/3 – the script now uses only 0 and 2).
- Placeholder values (e.g. `your_azure_devops_personal_access_token`) are treated as present; the script does not validate token authenticity.
- When auto‑prompting, press Enter to keep the existing masked value; entering text replaces it for the current session only (no file write‑back).
- To persist updated values back to `.env`, edit the file manually (future enhancement may automate this).

`doctor` is the simplest cross-platform pre‑flight; the PowerShell helper is ideal for Windows developer onboarding, local verification, or adding a lightweight gate in Azure DevOps / GitHub Actions Windows runners.

Interactive remediation (new):
```
# Launch diagnostics then open submenu
azuredevops-github-migration doctor --assist

Submenu options:
    1) Run PowerShell env loader (equivalent to update-env)
    2) Append missing canonical placeholders (--fix-env behavior)
    3) Re-run diagnostics (refresh the view)
    4) Quit

Placeholders (values beginning with the template prefixes, e.g. your_azure_devops_personal_access_token) are flagged as PLACEHOLDER so you know they still need real values.

Interactive .env editing (new) or via composite shortcut (`--doctor-mode edit` / `--doctor-mode edit-assist`):
```
# Safely edit required variables (tokens & org names) with backup (.env.bak.<UTC timestamp>)
azuredevops-github-migration doctor --edit-env

# Combine with placeholder append first (if you want canonical lines ensured)
azuredevops-github-migration doctor --fix-env --edit-env
```
Behavior:
* Prompts for each of the four canonical variables; press Enter to keep existing.
* Existing token/org values are shown masked (first 4 chars + ****).
* File ordering & comments are preserved when possible; missing canonical keys appended at end.
* A timestamped backup (`.env.bak.YYYYmmddHHMMSS`) is created before any write.
* After saving, diagnostics are re-run so you immediately see the updated environment status.
* Cannot be combined with `--json` (interactive session).

Difference vs `update-env`:
| Command | Purpose | Writes to `.env` | Creates Backup | Requires PowerShell |
|---------|---------|------------------|----------------|--------------------|
| `update-env` | Load & audit env via PowerShell script | No | No | Yes |
| `doctor --edit-env` | Edit & persist vars in pure Python | Yes | Yes | No |
```

Fixing missing environment placeholders (new):
```
# Append any missing canonical env variable placeholders (tokens/org names)
azuredevops-github-migration doctor --fix-env

# Combine with JSON output (added keys shown under fix_env.added)
azuredevops-github-migration doctor --fix-env --json
```
This does NOT overwrite existing secrets or alias values; it only appends placeholder lines for any of the four standard variables that are absent from the `.env` file. If an alias (e.g. `AZURE_DEVOPS_ORG`) exists but the canonical (`AZURE_DEVOPS_ORGANIZATION`) is missing, a placeholder for the canonical name is still appended so future tooling & docs remain consistent.

### Skipping Network Reachability Checks (Offline / Restricted)

If you're running in a locked-down environment (no direct egress to `api.github.com` or `dev.azure.com`) and only want to validate local configuration, add `--skip-network`:

```
azuredevops-github-migration doctor --skip-network
azuredevops-github-migration doctor --skip-network --fix-env --assist
```

When enabled, the "Network Reachability" section is replaced with a skipped notice.

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

### Interactive CLI & Environment Loader (New)

Two new convenience commands streamline onboarding and day-to-day usage:

| Command | Purpose | Notes |
|---------|---------|-------|
| `azuredevops-github-migration interactive` | Launch arrow-key navigable menu for common actions (init, analyze, migrate, batch, doctor, env update) | Requires optional dependency `questionary` (`pip install questionary`) |
| `azuredevops-github-migration update-env` | Runs underlying PowerShell helper (`scripts/Test-MigrationEnv.ps1 -Load -Overwrite -Json`) to load / audit env vars | Creates a stub `.env` if missing |

Why use them?
* Faster onboarding for new contributors (no need to memorize flags immediately)
* Ensures environment variables are loaded into the current process before running analysis or migrations
* Reduces copy/paste errors for common workflows

Non-Windows / PowerShell note:
* `update-env` requires PowerShell (pwsh preferred). If neither `pwsh` nor `powershell` is present, the command exits with an instructional message.
* The interactive menu works cross-platform; only the `update-env` action within it depends on PowerShell.

Security reminder: `update-env` never writes secret values back to the `.env` file—it only loads values that are already present (or that you manually added) and surfaces masked summaries.

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

## ✅ Post-Migration Verification

After each repository migration, validate success before announcing cutover. A detailed checklist lives in `docs/user-guide/POST_MIGRATION_CHECKLIST.md`.

### Scripted Verification (Recommended)
Use the helper script for a reproducible, machine-friendly summary:
```powershell
./scripts/verify-migration.ps1 -Org bet01 -Repo Rick
```
JSON output (for pipelines / dashboards):
```powershell
./scripts/verify-migration.ps1 -Org bet01 -Repo Rick -Json | ConvertFrom-Json
```
Exit codes: 0 = all good, 2 = warnings (non-fatal), 3 = fatal (repo inaccessible).

Quick verification (PowerShell – adjust variables):
```powershell
$Org = 'bet01'
$Repo = 'Rick'
# Repo metadata
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo" | Select-Object name, default_branch, visibility
# Branches & tags
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/branches?per_page=100" | Select-Object name | Sort-Object name
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/tags?per_page=100" | Select-Object name
# Workflows present?
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/contents/.github/workflows" | Select-Object name, path
# Latest workflow runs
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/actions/runs?per_page=3" | Select-Object -ExpandProperty workflow_runs | Select-Object name, status, conclusion, run_number | Format-Table
# Latest migration report summary (run inside repo root)
$latest = Get-ChildItem .\migration_reports -Filter "migration_report_*_${Repo}_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest) { (Get-Content $latest.FullName -Raw | ConvertFrom-Json) | Select-Object repository, project, pipelines_converted, branches_migrated, commits_migrated, issues_migrated }
```

If Git history was skipped (used `--no-git`), skip commit parity checks. Otherwise optionally mirror-clone and compare commit counts. See the full checklist for extended validation, issue migration checks, and sign‑off record.

### Advanced Automated Verification Additions

The verification script now supports deeper governance & quality checks and can be run locally or via a GitHub Action.

Key advanced capabilities:

| Feature | Parameters | Description |
|---------|------------|-------------|
| Branch Protection | `-CheckBranchProtection -BranchProtectionBranches main,release/*` | Verifies specified (or default) branches have protection enabled. Wildcards not expanded via API—list explicit branch names. |
| Tag Parity | `-ExpectedTagCount 42` or auto-detected | Compares enumerated tag count against expected (auto-filled from migration report `tags_count` if present). |
| Workflow Lint | `-LintWorkflows` | Basic structural lint: presence of `on:` and `jobs:` blocks, merge conflict markers, fetch failures. |
| Exit Control | `-FailOnBranchProtection -FailOnLintErrors -FailOnTagMismatch` | Promote specific discrepancies to fatal errors (exit 3). |
| Global Downgrade | `-WarnInsteadOfFail` | Downgrades any failing category (after detection) into warnings to keep pipeline green. |
| Summary File | `-SummaryFile verification-summary.json` | Writes full JSON to a static file (useful for artifacts). |

#### Example Local Runs
Branch protection + lint, fail hard on any issue:
```powershell
./scripts/verify-migration.ps1 -Org bet01 -Repo Rick `
    -CheckBranchProtection -BranchProtectionBranches main `
    -LintWorkflows `
    -FailOnBranchProtection -FailOnLintErrors
```

Tag parity with explicit count and write summary file (warnings only):
```powershell
./scripts/verify-migration.ps1 -Org bet01 -Repo Rick `
    -ExpectedTagCount 12 -LintWorkflows -WarnInsteadOfFail -SummaryFile verify.json -Json
```

Auto-detect expected tags from migration report (no explicit `-ExpectedTagCount` needed):
```powershell
./scripts/verify-migration.ps1 -Org bet01 -Repo Rick -LintWorkflows
```

#### Exit Codes (Extended Semantics)

| Code | Meaning |
|------|---------|
| 0 | All checks passed (or only info-level outputs) |
| 2 | Non-fatal warnings (missing optional components, downgraded failures) |
| 3 | Fatal condition (repo inaccessible OR selected FailOn* category triggered) |

#### PAT Scopes for Advanced Checks

| Feature | Additional GitHub Scope Needed? |
|---------|---------------------------------|
| Repo / Branch / Tags / Contents | `repo` covers it |
| Branch Protection Read | Usually included with `repo` (fine‑grained: Repository administration: Read) |
| Workflow Files / Runs | `repo` |

If branch protection API returns 404 despite repo visibility, ensure the token has repository administration read permission (fine‑grained tokens) or classic `repo` scope.

#### GitHub Action Automation

No migration-generated workflows are stored in this tool repository. An example reusable workflow (`examples/verify-migration-workflow.yml`) is provided—copy it into the **target migrated repository** as `.github/workflows/verify-migration.yml` if you want automated verification. Do **not** add converted pipeline workflows to the tool repo; they belong only in destination repos. The example triggers on pushes changing migration reports or the script, or via manual dispatch:

Manual dispatch inputs:
| Input | Description |
|-------|-------------|
| org | Target org/owner (defaults to repo owner if omitted) |
| repo | Target repository (defaults to current) |

The workflow:
1. Runs the PowerShell script in JSON mode.
2. Writes `verification-summary.json` as an artifact.
3. Posts a PR comment (if run within a PR) with truncated JSON summary.
4. Fails the job only if the script exit code maps to fatal (3) after considering selected fail flags.

To integrate into a migration PR, dispatch the workflow with desired inputs or let it auto-run when a new migration report is committed.

Fine‑tune behavior by editing the workflow and adding additional arguments (e.g. `-LintWorkflows`, `-CheckBranchProtection`).

---

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