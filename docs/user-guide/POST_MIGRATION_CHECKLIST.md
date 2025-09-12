Post-Migration Verification Checklist
====================================

Purpose: Provide a fast, repeatable validation that an Azure DevOps → GitHub migration succeeded (code, pipelines, and optionally issues). Run these steps per repository immediately after each migration and before handing off to application teams.

> TIP: Keep a copy of this file and tick items off. Fail fast—stop and remediate before proceeding if a critical item fails.

---
1. Core Repository Integrity
----------------------------
- [ ] Repository exists in target org: https://github.com/<github_org>/<repo>
- [ ] Description (if expected) copied
- [ ] Default branch matches source (usually main or master)
- [ ] Branch & tag counts are plausible vs Azure DevOps

PowerShell quick checks (replace variables):
```
$Org = 'bet01'
$Repo = 'Rick'
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo" | Select-Object name, default_branch, private, visibility
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/branches?per_page=100" | Select-Object name | Sort-Object name
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/tags?per_page=100" | Select-Object name
```

If Git history migrated (no --no-git) compare commit counts:
```
$Tmp = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "mig-verify-$Repo") -Force
Push-Location $Tmp.FullName
git clone --mirror https://github.com/$Org/$Repo.git
cd "$Repo.git"
(git rev-list --all --count) | ForEach-Object { "GitHub commit count: $_" }
Pop-Location
```

---
2. Workflow / Pipeline Conversion
---------------------------------
- [ ] .github/workflows/ directory exists
- [ ] Expected workflow file names present (e.g. rick.yml)
- [ ] Workflow YAML passes a dry parse (GitHub UI shows no schema errors)
- [ ] First workflow run triggered and succeeds or failures are understood

List workflow files via GitHub API:
```
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/contents/.github/workflows" | Select-Object name, path
```

Trigger a workflow run (if workflow_dispatch exists) or push a no-op:
```
# Example (commented out for safety):
# git clone https://github.com/$Org/$Repo.git
# cd $Repo
# Add-Content -Path README.md -Value "`n# verification $(Get-Date -Format o)"; git add README.md; git commit -m "chore: trigger workflow"; git push
```

Check latest workflow runs:
```
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/actions/runs?per_page=5" | Select-Object -ExpandProperty workflow_runs | Select-Object name, status, conclusion, run_number | Format-Table
```

---
3. Migration Report Validation
------------------------------
- [ ] JSON report file created in migration_reports/
- [ ] pipelines_converted: true (when expected)
- [ ] Commit / branch counts (if Git migrated) match sampled GitHub data
- [ ] errors array empty or only contains accepted exceptions

Example:
```
Get-ChildItem .\migration_reports -Filter "migration_report_*_${Repo}_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object {
  $report = Get-Content $_.FullName -Raw | ConvertFrom-Json
  $report | Select-Object repository, project, pipelines_converted, branches_migrated, commits_migrated, issues_migrated
  if ($report.errors) { Write-Warning "Reported errors:"; $report.errors }
}
```

---
4. Issues (If Migrated)
-----------------------
- [ ] Expected number of issues roughly matches Azure DevOps work items migrated
- [ ] Labels applied (type / state / priority) as per mapping
- [ ] Markdown rendering acceptable
- [ ] Cross-links preserved via text references (if implemented)

Commands:
```
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/issues?state=all&per_page=100" | Measure-Object | Select-Object Count
Invoke-RestMethod "https://api.github.com/repos/$Org/$Repo/labels?per_page=100" | Select-Object name
```

If using Jira or --no-issues: mark Not in scope.

---
5. Security & Settings
----------------------
- [ ] Required branch protection rules recreated
- [ ] Secrets needed by workflows configured (Settings → Secrets and variables → Actions)
- [ ] Actions permissions allow the workflow to run
- [ ] Default permissions for GITHUB_TOKEN reviewed
- [ ] Optional: Dependabot / code scanning enabled

---
6. Housekeeping
---------------
- [ ] Legacy Azure DevOps pipeline disabled
- [ ] Team notified of cutover
- [ ] Documentation updated (README build badges, contribution guidelines)
- [ ] Optional: Archive Azure DevOps repo after stabilization window

---
7. Sign-Off Record
------------------
| Item | Result | Notes | Checked By | Date |
|------|--------|-------|------------|------|
| Repository created |  |  |  |  |
| Branches & tags |  |  |  |  |
| Git history parity |  |  |  |  |
| Workflow file(s) present |  |  |  |  |
| Workflow run succeeded |  |  |  |  |
| Issues migrated (if in scope) |  |  |  |  |
| Labels correct |  |  |  |  |
| Report reviewed |  |  |  |  |
| Secrets configured |  |  |  |  |
| Branch protections |  |  |  |  |
| ADO pipeline disabled |  |  |  |  |
| Final approval |  |  |  |  |

---
8. Automation Ideas (Future)
----------------------------
- Script to diff commit counts automatically from latest report vs GitHub API
- GitHub Action to validate presence of required secrets before enabling workflows
- Aggregated dashboard summarizing migration status across repos

---
9. Quick Reference of Key CLI Flags
-----------------------------------
| Flag | Purpose |
|------|---------|
| --no-git | Skip Git history |
| --no-issues | Force-disable issue migration |
| --pipelines-scope repository | Limit pipeline conversion to repo-level only |
| --exclude-disabled-pipelines | Ignore disabled / paused pipelines |
| --verify-remote | Post-push verification |
| --dry-run | Simulate without remote changes |

---
10. Troubleshooting Quick Hints
-------------------------------
- Missing workflow: Re-run migration after workflow auto-commit feature, or manually commit YAML.
- Workflow failed: Likely secret / runner image mismatch—check runs-on and secrets.
- Commit discrepancy: Confirm you did not use --no-git; inspect report JSON for commits_migrated.
- No issues migrated but expected: Ensure config migrate_work_items=true and you did not pass --no-issues / --skip-work-items during analysis.

---
Done? Archive this checklist with the migration report for audit.
