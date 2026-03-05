# Enterprise Migration Design: 700+ Repos from Azure DevOps to GitHub

**Date:** 2026-03-05
**Status:** Approved
**Author:** Claude Code + Stewart Burton

## Context

Migrate 700+ repositories from Azure DevOps to GitHub. Azure DevOps pipelines will remain in ADO for now (repos move, builds stay). GitHub org is already set up with SSO/SAML. Repos need a hard freeze during migration.

## Constraints

- Repos stay on GitHub; build pipelines stay in ADO (for now)
- Hard freeze required: automate ADO permission denial during migration
- Must be resumable: failures at repo 350 cannot require restarting from repo 1
- Teams need advance notice and clear instructions
- Rollback capability for failed migrations

---

## Part 1: Code Refactoring

### 1.1 Break up migrate.py (1495 lines)

Current `migrate.py` contains 5 classes. Split into focused modules:

```
src/azuredevops_github_migration/
  clients/
    __init__.py
    azure_devops.py       # AzureDevOpsClient
    github.py             # GitHubClient
  git_migrator.py         # GitMigrator
  pipeline_converter.py   # PipelineConverter
  orchestrator.py         # MigrationOrchestrator
  exceptions.py           # AuthenticationError, MigrationError, RateLimitError, GitOperationError
  config.py               # Config loading, env substitution, .env parsing (deduplicated)
  state.py                # NEW: Migration state persistence
  freeze.py               # NEW: ADO repo permission management
  notifications.py        # NEW: Team notification engine
  verify.py               # NEW: Post-migration verification
```

Keep `migrate.py` as a backward-compatible wrapper that re-exports from the new modules.

### 1.2 Deduplicate shared logic

| Duplicated Logic | Current Locations | New Location |
|---|---|---|
| `.env` file loading | `migrate.py`, `analyze.py` | `config.py` |
| Env-var substitution | `migrate.py`, `utils.py` | `config.py` |
| Config validation | `migrate.py`, `utils.py` | `config.py` |

### 1.3 Fix existing issues

- Remove unused imports: `asyncio`, `ThreadPoolExecutor` in migrate.py
- Fix report version: hardcoded `'2.0.0'` -> read from `__version__`
- Fix test import paths: `src.migrate` -> `azuredevops_github_migration.migrate`
- Move 40+ unrelated GitHub Actions workflows to separate repo or `.github/workflows/archived/`
- Fix `batch_migrate.py` to pass `migrate_pipelines` and `dry_run` to orchestrator
- Cache `get_user()` result in GitHubClient (called redundantly per repo)

---

## Part 2: New Features

### 2.1 Migration State Persistence (P0)

JSON-file state tracker that survives crashes.

**State file format:** `migration_state_{wave}_{timestamp}.json`

```json
{
  "migration_id": "uuid",
  "wave": "wave_03",
  "started_at": "2026-03-05T10:00:00Z",
  "config_file": "config.json",
  "total_repos": 50,
  "repos": {
    "ProjectA/repo-1": {
      "status": "completed",
      "github_url": "https://github.com/org/repo-1",
      "github_repo_name": "repo-1",
      "frozen_at": "2026-03-05T09:30:00Z",
      "migration_started": "2026-03-05T10:01:00Z",
      "migration_completed": "2026-03-05T10:04:23Z",
      "branches_migrated": 12,
      "commits_migrated": 1543,
      "verification": {"branch_match": true, "commit_match": true}
    },
    "ProjectA/repo-2": {
      "status": "failed",
      "error": "Git push timeout after 1800s",
      "retry_count": 1,
      "last_attempt": "2026-03-05T10:15:00Z"
    },
    "ProjectB/repo-3": {
      "status": "pending"
    },
    "ProjectB/repo-4": {
      "status": "in_progress",
      "step": "pushing_git_history",
      "migration_started": "2026-03-05T10:20:00Z"
    }
  }
}
```

**CLI behavior:**
- `--state-file X` flag on batch command
- Auto-skips `completed` repos on restart
- `--retry-failed` retries only `failed` repos
- `--resume` continues from `in_progress` (marks as failed first, then retries)
- State file written atomically (write to temp, rename) to prevent corruption

### 2.2 ADO Repo Hard Freeze (P0)

Uses Azure DevOps Security REST API to deny push permissions.

**Mechanism:**
1. Save current ACLs for the repo's Contributors group
2. Set `GenericContribute` permission to `Deny` for `[{Project}]\Contributors`
3. Store saved ACLs in state file for later restore

**API calls:**
```
GET  https://dev.azure.com/{org}/_apis/accesscontrollists/{securityNamespaceId}?token={repoToken}
POST https://dev.azure.com/{org}/_apis/accesscontrolentries/{securityNamespaceId}
```

Git Repositories security namespace ID: `2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87`

**New CLI commands:**
```bash
ado2gh-freeze --plan wave.json --config config.json     # Freeze all repos in plan
ado2gh-freeze --project X --repo Y --config config.json # Freeze single repo
ado2gh-unfreeze --plan wave.json --config config.json   # Restore original permissions
ado2gh-unfreeze --project X --repo Y --config config.json
```

**PAT scope required:** `Security (Read & Manage)`, `Identity (Read)`

### 2.3 Parallel Batch Migration (P0)

Replace sequential loop with `concurrent.futures.ThreadPoolExecutor`.

```python
with ThreadPoolExecutor(max_workers=concurrency) as executor:
    futures = {}
    for repo in plan:
        future = executor.submit(migrate_single_repo, repo, config, state)
        futures[future] = repo

    for future in as_completed(futures):
        repo = futures[future]
        try:
            result = future.result()
            state.mark_completed(repo)
        except Exception as e:
            state.mark_failed(repo, str(e))
```

- Default concurrency: 4 (configurable via `--concurrency N`)
- Each thread gets its own temp directory
- State file updates are thread-safe (lock around writes)
- Rate limiter is shared across threads
- CLI: `ado2gh-batch --plan X --concurrency 4`

### 2.4 Rollback on Failure (P1)

When migration fails:
1. Delete the partially-created GitHub repo (if created by our tool, tracked in state)
2. Unfreeze the ADO repo (restore saved ACLs)
3. Mark as `failed` in state file

CLI: `ado2gh-rollback --state-file X --config config.json`
- Rolls back all `failed` repos
- Or: `--project X --repo Y` for single repo rollback

### 2.5 CLI Status Dashboard (P1)

```bash
$ ado2gh-status --state-file migration_state.json

Migration: wave_03 | Started: 2026-03-05 10:00 UTC | Running: 1h 23m
================================================================
Total:       50
Completed:   32  [################............] 64.0%
In Progress:  4  api-gateway, user-service, auth-lib, payments
Failed:       2  legacy-monorepo (timeout), config-svc (403)
Pending:     12

Throughput: 2.1 repos/min | ETA: ~6 min remaining

Recent errors:
  ProjectA/legacy-monorepo: Git push timed out (repo is 4.2GB) [retry 1/3]
  ProjectB/config-svc: GitHub 403 Forbidden - check PAT scopes
```

### 2.6 Post-Migration Verification (P1)

Automated checks after each repo migration:

```bash
ado2gh-verify --state-file X --config config.json
```

Per repo:
- GitHub repo exists and is accessible
- Branch count matches ADO source
- Commit count matches (via `git rev-list --all --count`)
- Default branch name matches
- Repository is not empty
- Tags count matches (if applicable)

Results stored in state file under `verification` key.

### 2.7 Pre-Migration Checks (P1)

```bash
ado2gh-precheck --plan wave.json --config config.json
```

Per repo:
- Open pull request count (warn if > 0)
- Active branch count
- Repo size (warn if > 1GB)
- GitHub repo name conflict check
- Estimated migration time

### 2.8 Team Notification Engine (P2)

Template-based notifications:

```bash
ado2gh-notify --plan wave.json --template announcement --config config.json
ado2gh-notify --plan wave.json --template reminder --config config.json
ado2gh-notify --plan wave.json --template completion --state-file X --config config.json
```

Templates stored in `templates/notifications/`:
- `announcement.md` - 2 weeks before
- `reminder.md` - 1 week before
- `completion.md` - after migration
- `postponed.md` - if wave rolled back

Output: Markdown files per team (operator sends via Outlook/Teams/Slack manually, or integrates with email API).

### 2.9 ADO Pipeline Repointing (P2, future)

```bash
ado2gh-repoint-pipelines --project X --repo Y --github-repo Z --config config.json
```

1. Create/find GitHub service connection in ADO project
2. Update pipeline YAML repository references
3. Trigger test build to verify

### 2.10 GitHub Repo Configuration (P2)

```bash
ado2gh-configure --state-file X --branch-protection main --require-reviews 1
ado2gh-configure --state-file X --assign-team "platform-team" --permission write
```

---

## Part 3: Migration Process

### Phase 0: Discovery & Planning (Week 1-2)

1. Run org-wide analysis:
   ```bash
   ado2gh-analyze --create-plan --format csv --config config.json --skip-work-items
   ```

2. From the CSV output, create a spreadsheet with every repo:
   - Project, repo name, size, branch count, PR count, priority, estimated effort

3. Categorize repos into waves:
   - Wave 1 (Pilot): 5-10 low-risk repos from a willing team
   - Wave 2-3 (Early adopters): 30-50 repos per wave
   - Wave 4-N (Bulk): 50-100 repos per wave, grouped by ADO project
   - Final wave: Special cases (LFS, very large, complex deps)

4. For each wave, create a plan JSON file:
   ```json
   [
     {
       "project_name": "Platform",
       "repo_name": "api-gateway",
       "github_repo_name": "api-gateway",
       "team_contact": "alice@company.com",
       "team_name": "Platform Engineering"
     }
   ]
   ```

5. Map ADO teams to GitHub teams (ensure every dev has GitHub SSO access)

### Phase 1: Communication (T-14 days per wave)

**T-14 days:** Send announcement email to team leads.

Key points:
- List of specific repos being migrated
- Migration date and freeze window
- Action items: verify GitHub access, merge open PRs, stop commits at freeze time
- What stays the same: ADO build pipelines continue working
- Post-migration: how to update git remotes

**T-7 days:** Send reminder. Run pre-check to identify open PRs.

**T-1 day:** Final confirmation. Verify:
- All team leads acknowledged
- Open PR count is zero or accepted
- Migration VM healthy
- GitHub API rate limit sufficient
- Disk space sufficient

### Phase 2: Migration Execution (per wave)

**Step 1: Pre-flight (T-30 min)**
```bash
ado2gh-migrate --validate-only --config config.json
gh api /rate_limit --jq '.rate.remaining'  # Need > 4000
```

**Step 2: Freeze (T-0)**
```bash
ado2gh-freeze --plan wave_N_plan.json --config config.json
```
Verify: try pushing to a frozen repo - should get permission denied.

**Step 3: Migrate (T+5 min)**
```bash
ado2gh-batch --plan wave_N_plan.json --config config.json \
  --concurrency 4 --state-file wave_N_state.json
```
Monitor: `ado2gh-status --state-file wave_N_state.json`

Expected: ~2-5 min per repo. 50 repos at concurrency 4 = ~30-60 minutes.

**Step 4: Handle failures (T+60 min)**
```bash
ado2gh-batch --state-file wave_N_state.json --retry-failed --config config.json
```
For persistent failures: unfreeze that repo, defer to next wave.

**Step 5: Verify (T+90 min)**
```bash
ado2gh-verify --state-file wave_N_state.json --config config.json
```
Plus manual spot-check of 2-3 repos.

**Step 6: Configure GitHub repos (T+120 min)**
```bash
ado2gh-configure --state-file wave_N_state.json \
  --branch-protection main --require-reviews 1
```

**Step 7: Notify teams (T+150 min)**
```bash
ado2gh-notify --plan wave_N_plan.json --template completion \
  --state-file wave_N_state.json
```

### Phase 3: Post-Migration (T+24h per wave)

1. Monitor for team issues (Slack channel / email)
2. Verify ADO pipelines still trigger correctly
3. Archive ADO repos (set to disabled/read-only)
4. Update tracking spreadsheet
5. Run retrospective: what went well, what to improve for next wave

### Phase 4: Pipeline Repointing (future, separate track)

1. Create GitHub service connections in ADO projects
2. Update pipeline YAML to reference GitHub repos
3. Test that builds still pass
4. (Eventually) Convert ADO pipelines to GitHub Actions

---

## Part 4: Rollback Procedure

If > 30% of repos in a wave fail:

1. STOP batch migration (Ctrl+C)
2. Unfreeze all repos: `ado2gh-unfreeze --plan wave.json --config config.json`
3. Delete partial GitHub repos: `ado2gh-rollback --state-file X --config config.json`
4. Notify teams: `ado2gh-notify --plan wave.json --template postponed`
5. Investigate, fix, reschedule

---

## Part 5: Edge Cases

| Scenario | Handling |
|---|---|
| Repo > 1GB | Migrate alone, longer timeout (3600s), not in parallel |
| Git LFS repo | Requires `git lfs install`, separate LFS object migration |
| Empty repo | Skip (mark "skipped" in state) or create empty GitHub repo |
| GitHub name conflict | Prompt operator: skip, rename, or overwrite |
| Team refuses to merge PRs | Document open PRs in report, proceed anyway |
| ADO permissions block freeze | Escalate to ADO admin, use soft freeze for that wave |
| GitHub rate limit hit | Auto-pause, wait for reset, resume from state file |
| Migration VM crashes | Restart from state file |
| Very old repo (2010+) | May have encoding issues in filenames; test first |
| Repo with submodules | Submodule URLs may need updating post-migration |
| Fork relationships | ADO forks don't transfer; document and handle manually |

---

## Part 6: Timeline

```
Week 1-2:  Tool refactoring + new features (state, freeze, parallel, rollback)
Week 3:    Discovery run + wave planning + GitHub org verification
Week 4:    Wave 1 pilot (5-10 repos)
Week 5:    Waves 2-3 (30-50 repos each)
Week 6-8:  Waves 4-N (100 repos/week)
Week 9:    Final wave (special cases) + cleanup
Week 10+:  ADO pipeline repointing (separate track)
```

---

## Part 7: Feature Priority Matrix

| Priority | Feature | Effort | Required For |
|---|---|---|---|
| P0 | Code refactor (split monolith) | Medium | Maintainability |
| P0 | State persistence + resume | Medium | Batch reliability |
| P0 | ADO repo hard freeze | Medium | Data integrity |
| P0 | Parallel batch migration | Low | Performance |
| P1 | Rollback on failure | Medium | Safety |
| P1 | CLI status dashboard | Low | Operator visibility |
| P1 | Post-migration verification | Low | Quality assurance |
| P1 | Pre-migration checks (open PRs) | Low | Risk reduction |
| P2 | Team notification engine | Medium | Communication |
| P2 | ADO pipeline repointing | High | Pipeline continuity |
| P2 | GitHub repo configuration (branch protection, teams) | Medium | Security |
| P3 | Migration audit log / CSV export | Low | Reporting |
| P3 | Web dashboard | High | Nice-to-have |
