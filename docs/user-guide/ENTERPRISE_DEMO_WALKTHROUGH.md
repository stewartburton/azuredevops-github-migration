# Enterprise Migration Demo Walkthrough

Step-by-step guide for running a large-scale Azure DevOps to GitHub migration (700+ repos) using the v3.0.0 enterprise lifecycle: analyze, freeze, batch migrate, monitor, verify, unfreeze.

**Audience:** DevOps engineers executing production migrations.

**Lifecycle overview:**

```
Analyze --> Plan --> Dry Run --> Freeze --> Batch Migrate --> Monitor --> Retry --> Verify --> Unfreeze
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python >= 3.8 | 3.8-3.12 supported |
| Git | In PATH |
| Azure DevOps PAT | Code (Read/Write), Project & Team (Read), **Security (Manage)** for freeze |
| GitHub PAT | `repo` scope (add `admin:org` if creating repos in the org) |
| Disk space | Enough for largest repository clone |

Install:

```bash
pip install azuredevops-github-migration
azuredevops-github-migration --version   # should print v3.0.0+
```

---

## Step 1: Initialize and Configure

```bash
azuredevops-github-migration init --template jira-users
```

Edit `.env` with your values:

```
AZURE_DEVOPS_PAT=xxxx
GITHUB_TOKEN=ghp_xxxx
AZURE_DEVOPS_ORGANIZATION=contoso-dev
GITHUB_ORGANIZATION=contoso
```

Edit `config.json` (excerpt):

```json
{
  "azure_devops": {
    "organization": "${AZURE_DEVOPS_ORGANIZATION}",
    "project": "WebPlatform"
  },
  "github": {
    "organization": "${GITHUB_ORGANIZATION}",
    "create_private_repos": true
  },
  "migration": {
    "migrate_work_items": false,
    "migrate_pipelines": true
  }
}
```

Run diagnostics to verify setup:

```bash
azuredevops-github-migration doctor
```

All four checks (PAT, TOKEN, ADO org, GH org) should show `OK`.

---

## Step 2: Analyze and Plan

For a single project:

```bash
azuredevops-github-migration analyze --project "WebPlatform" --create-plan --skip-work-items
```

For an entire organization (700+ repos):

```bash
azuredevops-github-migration analyze --create-plan --skip-work-items
```

This produces a migration plan JSON file (e.g., `migration_plan_contoso-dev_WebPlatform.json`). Each entry looks like:

```json
{
  "project_name": "WebPlatform",
  "repo_name": "frontend-app",
  "github_repo_name": "frontend-app",
  "migrate_issues": false,
  "migrate_pipelines": true,
  "description": "React frontend application"
}
```

Review the plan and adjust `github_repo_name` or remove repos you want to skip.

---

## Step 3: Dry Run (Validate One Repo)

Test a single repo before committing to batch:

```bash
azuredevops-github-migration migrate --project "WebPlatform" --repo "frontend-app" --dry-run
```

This validates connectivity, PAT permissions, and repo structure without making any changes on GitHub.

---

## Step 4: Freeze Source Repos

Lock all repos in the plan to prevent pushes during migration:

```bash
azuredevops-github-migration freeze \
  --plan migration_plan_contoso-dev_WebPlatform.json \
  --config config.json \
  --state-file migration_state.json
```

Output:

```
[FREEZE] WebPlatform/frontend-app
[FREEZE] WebPlatform/api-service
[FREEZE] WebPlatform/shared-libs
[FREEZE] WebPlatform/infra-config
```

**What happens:** The tool uses the Azure DevOps Security REST API to set a deny ACE on the `GenericContribute` permission (bit 4) in the Git Repositories security namespace (`2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87`). Original ACLs are saved to the state file so they can be restored later.

**Required PAT scope:** Security (Manage) on the Azure DevOps organization.

**Standalone entry point:** `ado2gh-freeze --plan ... --config ... --state-file ...`

---

## Step 5: Batch Migrate

Run a dry run first to validate all repos:

```bash
azuredevops-github-migration batch \
  --plan migration_plan_contoso-dev_WebPlatform.json \
  --config config.json \
  --state-file migration_state.json \
  --concurrency 4 \
  --dry-run
```

Then execute the real migration:

```bash
azuredevops-github-migration batch \
  --plan migration_plan_contoso-dev_WebPlatform.json \
  --config config.json \
  --state-file migration_state.json \
  --concurrency 4 \
  --wave wave-1
```

### Batch Flags

| Flag | Purpose | Default |
|------|---------|---------|
| `--concurrency N` | Parallel migration threads | 4 |
| `--state-file F` | State file for resume/tracking | `migration_state_<wave>.json` |
| `--wave NAME` | Wave label in state file | `default` |
| `--dry-run` | Simulate without changes | off |
| `--retry-failed` | Re-attempt only failed repos | off |
| `--create-sample` | Generate a sample plan file | off |

The state file is a thread-safe JSON file. Each repo is tracked as `pending`, `in_progress`, `completed`, or `failed`. If the process is interrupted, re-running the same command skips completed repos and resumes from where it left off.

**Standalone entry point:** `ado2gh-batch --plan ... --config ...`

---

## Step 6: Monitor Progress

Check migration status at any time:

```bash
azuredevops-github-migration status --state-file migration_state.json
```

Sample output:

```
Migration: wave-1 | ID: a1b2c3d4
============================================================
Total:       47
Completed:     42  [##################################......] 89.4%
In Progress:    1  WebPlatform/infra-config
Failed:         2
Pending:        2
Skipped:        0
```

To see error details:

```bash
azuredevops-github-migration status --state-file migration_state.json --show-errors
```

```
Errors:
  WebPlatform/legacy-tools: git clone timeout (retry 1)
  WebPlatform/archive-data: permission denied (retry 0)
```

**Standalone entry point:** `ado2gh-status --state-file ...`

---

## Step 7: Handle Failures

Re-attempt only the failed repos:

```bash
azuredevops-github-migration batch \
  --plan migration_plan_contoso-dev_WebPlatform.json \
  --config config.json \
  --state-file migration_state.json \
  --retry-failed
```

The `--retry-failed` flag filters to repos with `failed` status only. Completed repos are never re-run. The state file increments `retry_count` for each attempt.

Repeat until all repos are completed or failures are resolved manually.

---

## Step 8: Verify Migration

Compare branches between ADO source and GitHub target:

```bash
azuredevops-github-migration verify \
  --state-file migration_state.json \
  --config config.json
```

The tool runs `git ls-remote --heads` against both remotes and reports:
- Number of branches on each side
- Whether branches match
- Any branches missing on GitHub
- Any extra branches on GitHub

**Standalone entry point:** `ado2gh-verify --state-file ... --config ...`

---

## Step 9: Unfreeze Source Repos

Restore original permissions on ADO repos:

```bash
azuredevops-github-migration unfreeze \
  --plan migration_plan_contoso-dev_WebPlatform.json \
  --config config.json \
  --state-file migration_state.json
```

Output:

```
[UNFREEZE] WebPlatform/frontend-app
[UNFREEZE] WebPlatform/api-service
[UNFREEZE] WebPlatform/shared-libs
[UNFREEZE] WebPlatform/infra-config
```

Only repos with saved ACLs in the state file are restored. Repos without saved ACLs show `[SKIP]`.

**Standalone entry point:** `ado2gh-unfreeze --plan ... --config ... --state-file ...`

---

## Quick Reference

### Lifecycle Commands

| Step | Command |
|------|---------|
| Init | `azuredevops-github-migration init --template jira-users` |
| Doctor | `azuredevops-github-migration doctor` |
| Analyze | `azuredevops-github-migration analyze --project P --create-plan` |
| Dry run | `azuredevops-github-migration migrate --project P --repo R --dry-run` |
| Freeze | `azuredevops-github-migration freeze --plan PLAN --config C --state-file S` |
| Batch | `azuredevops-github-migration batch --plan PLAN --config C --state-file S` |
| Status | `azuredevops-github-migration status --state-file S` |
| Retry | `azuredevops-github-migration batch --plan PLAN --config C --state-file S --retry-failed` |
| Verify | `azuredevops-github-migration verify --state-file S --config C` |
| Unfreeze | `azuredevops-github-migration unfreeze --plan PLAN --config C --state-file S` |

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

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `403` on freeze/unfreeze | PAT missing Security (Manage) scope | Regenerate PAT with Security (Manage) scope |
| `PermissionError` on state file (Windows) | File locked by another process | Tool retries automatically (5 attempts); check antivirus |
| `git ls-remote` timeout | Large repo or network issue | Increase timeout; check firewall/proxy settings |
| Batch exits with code 1 | Some repos failed | Run `status --show-errors`, then `batch --retry-failed` |
| `[SKIP] no saved ACLs` on unfreeze | State file missing freeze data | Ensure same `--state-file` used for both freeze and unfreeze |
| `401` on analyze/migrate | Invalid or expired PAT | Regenerate PAT; verify org name in `.env` |
| Repos still writable after freeze | Freeze failed silently | Check freeze output for `[FAIL]` lines; verify PAT scope |

---

## Further Reading

- [HOW_TO_GUIDE.md](HOW_TO_GUIDE.md) -- detailed flag reference and scenarios
- [PRE_MIGRATION_CHECKLIST.md](PRE_MIGRATION_CHECKLIST.md) -- 100+ item pre-migration checklist
- [POST_MIGRATION_CHECKLIST.md](POST_MIGRATION_CHECKLIST.md) -- post-migration validation steps
- [README.md](../../README.md) -- installation, configuration, and project overview
