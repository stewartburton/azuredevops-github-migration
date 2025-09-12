<#!
.SYNOPSIS
  Post-migration verification for Azure DevOps -> GitHub repo.

.DESCRIPTION
  Checks repository existence, branches, workflow files, recent runs, and summarizes
  latest migration report. Designed to be idempotent, read-only (no pushes) and
  usable in CI or local shells.

.PARAMETER Org
  GitHub organization / owner (e.g. bet01)

.PARAMETER Repo
  GitHub repository name

.PARAMETER ReportProject
  Azure DevOps project name used in migration (defaults to same as in report detection logic)

.PARAMETER ReportPrefix
  Prefix pattern for migration report files (default: migration_report_)

.PARAMETER Token
  GitHub token (falls back to $Env:GITHUB_TOKEN if omitted). Needs 'repo' scope for private repos.

.PARAMETER Json
  Output machine readable JSON summary instead of human text (still writes warnings to stderr).

.EXAMPLE
  ./scripts/verify-migration.ps1 -Org bet01 -Repo Rick

.EXAMPLE
  ./scripts/verify-migration.ps1 -Org bet01 -Repo Rick -Json | jq .

.NOTES
  Exit codes: 0 success, 2 partial (warnings), 3 fatal (e.g. repo not found without auth).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Org,
  [Parameter(Mandatory)][string]$Repo,
  [string]$ReportProject = '*',
  [string]$ReportPrefix = 'migration_report_',
  [string]$Token = $Env:GITHUB_TOKEN,
  [switch]$Json,
  [switch]$LoadDotEnv,
  # --- Advanced / Optional ---
  [switch]$CheckBranchProtection,
  [string[]]$BranchProtectionBranches = @(),
  [int]$ExpectedTagCount,
  [int]$MaxTagPages = 5,
  [switch]$LintWorkflows,
  [string]$SummaryFile,
  [switch]$FailOnBranchProtection,
  [switch]$FailOnLintErrors,
  [switch]$FailOnTagMismatch,
  [switch]$WarnInsteadOfFail,
  # (Secrets logic removed for simplification)
  [string]$AzureDevOpsOrg,
  [string]$AzureDevOpsProject,
  [string]$AzureDevOpsPat = $Env:AZURE_DEVOPS_PAT,
  [switch]$DetectAdoSources,
  [string]$TextReportFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($Title) { Write-Host "`n=== $Title ===" -ForegroundColor Cyan }
function Warn($m) { Write-Warning $m }
function Fail($m) { Write-Error $m; exit 3 }
function SafeCount($x) {
  if ($null -eq $x) { return 0 }
  if ($x -is [string]) { return 1 }
  try { return (@($x)).Count } catch { return 0 }
}

if ($LoadDotEnv -and -not $Token -and (Test-Path .env)) {
  try {
    Get-Content .env | ForEach-Object {
      if ($_ -match '^(?<k>[^#=]+)=(?<v>.*)$') {
        $k=$Matches.k.Trim(); $v=$Matches.v.Trim(); if ($k -and -not (Test-Path env:$k)) { [Environment]::SetEnvironmentVariable($k,$v) }
      }
    }
    if (-not $Token -and $Env:GITHUB_TOKEN) { $Token = $Env:GITHUB_TOKEN }
  } catch { Warn 'Failed to parse .env file.' }
}

if (-not $Token) { Warn 'No token supplied; private repositories will 404 (GitHub returns 404 to mask existence).'; }

function Invoke-GH([string]$Uri) {
  $Headers = @{ 'Accept' = 'application/vnd.github+json'; 'User-Agent' = 'migration-verifier' }
  if ($Token) { $Headers['Authorization'] = "Bearer $Token" }
  try { return Invoke-RestMethod -Uri $Uri -Headers $Headers -ErrorAction Stop }
  catch {
    throw
  }
}

$summary = [ordered]@{
  org = $Org
  repo = $Repo
  timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
  repository_found = $false
  default_branch = $null
  branch_count = $null
  workflow_files = @()
  workflow_run_count = $null
  last_workflow_run = $null
  last_workflow_conclusion = $null
  last_workflow_age_minutes = $null
  latest_report_file = $null
  report = [ordered]@{}
  warnings = @()
  branch_protection_failures = @()
  workflow_lint = @{}
  tag_count = $null
  expected_tag_count = $null
  tags_match_expected = $null
  ado_variable_groups = @()
  ado_variables = @()
  ado_service_connections = @()
}

Write-Section 'Repository'
try {
  $repoMeta = Invoke-GH "https://api.github.com/repos/$Org/$Repo"
  $summary.repository_found = $true
  $summary.default_branch = $repoMeta.default_branch
  Write-Host "Repo: $($repoMeta.full_name) (default=$($repoMeta.default_branch))" -ForegroundColor Green
} catch {
  Warn "Repository $Org/$Repo not accessible (private without token, wrong name, or missing)."
  $summary.warnings += 'repository_not_accessible'
}

Write-Section 'Branches'
try {
  $branches = Invoke-GH "https://api.github.com/repos/$Org/$Repo/branches?per_page=100"
  $summary.branch_count = (SafeCount $branches)
  $branches | Select-Object -ExpandProperty name | Sort-Object | ForEach-Object { Write-Host " - $_" }
} catch {
  Warn 'Failed to enumerate branches.'
  $summary.warnings += 'branches_list_failed'
}

Write-Section 'Workflow Files'
try {
  $wf = Invoke-GH "https://api.github.com/repos/$Org/$Repo/contents/.github/workflows"
  $files = $wf | Where-Object { $_.type -eq 'file' } | Select-Object -ExpandProperty name
  $script:workflowEntries = $wf
  $summary.workflow_files = $files
  if (-not $files) { Warn 'No workflow files found.'; $summary.warnings += 'no_workflow_files' }
  else { $files | ForEach-Object { Write-Host " - $_" } }
} catch {
  Warn 'Workflow directory missing or not accessible.'
  $summary.warnings += 'workflows_dir_missing'
}

Write-Section 'Recent Workflow Runs'
try {
  $runs = Invoke-GH "https://api.github.com/repos/$Org/$Repo/actions/runs?per_page=5"
  $summary.workflow_run_count = $runs.total_count
  $latestRun = $runs.workflow_runs | Sort-Object run_number -Descending | Select-Object -First 1
  if ($latestRun) {
    $summary.last_workflow_run = $latestRun.name
    $summary.last_workflow_conclusion = $latestRun.conclusion
    $age = (Get-Date).ToUniversalTime() - ([DateTime]$latestRun.created_at)
    $summary.last_workflow_age_minutes = [Math]::Round($age.TotalMinutes,2)
  }
  $runs.workflow_runs | Select-Object name, status, conclusion, run_number, created_at | Format-Table
  if ($runs.total_count -eq 0) { $summary.warnings += 'no_workflow_runs' }
} catch {
  Warn 'Could not fetch workflow runs.'
  $summary.warnings += 'workflow_runs_failed'
}


# --- Azure DevOps Source Detection ---
if ($DetectAdoSources -and $AzureDevOpsOrg -and $AzureDevOpsProject -and $AzureDevOpsPat) {
  Write-Section 'Azure DevOps Variable & Connection Scan'
  $adoBase = "https://dev.azure.com/$AzureDevOpsOrg/$AzureDevOpsProject/_apis"
  $adoHeaders = @{ Authorization = ("Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$AzureDevOpsPat"))); 'User-Agent'='migration-verifier' }
  try {
    $vgUri = "$adoBase/distributedtask/variablegroups?api-version=7.1-preview.2"
    $vg = Invoke-RestMethod -Uri $vgUri -Headers $adoHeaders -ErrorAction Stop
    if ($vg.value) {
      $summary.ado_variable_groups = $vg.value.name
      foreach ($g in $vg.value) { if ($g.variables) { $summary.ado_variables += $g.variables.PSObject.Properties.Name } }
    }
  } catch { Warn 'Failed to fetch variable groups.'; $summary.warnings += 'ado_variable_groups_fetch_failed' }
  try {
    $scUri = "$adoBase/serviceendpoint/endpoints?api-version=7.1-preview.4"
    $sc = Invoke-RestMethod -Uri $scUri -Headers $adoHeaders -ErrorAction Stop
    if ($sc.value) { $summary.ado_service_connections = $sc.value.name }
  } catch { Warn 'Failed to fetch service connections.'; $summary.warnings += 'ado_service_connections_fetch_failed' }
}

# --- Branch Protection ---
if ($CheckBranchProtection) {
  Write-Section 'Branch Protection'
  $branchesToCheck = @()
  if ((SafeCount $BranchProtectionBranches) -gt 0) { $branchesToCheck += $BranchProtectionBranches }
  elseif ($summary.default_branch) { $branchesToCheck += $summary.default_branch }
  $branchesToCheck = $branchesToCheck | Sort-Object -Unique
  foreach ($b in $branchesToCheck) {
    try {
      $prot = Invoke-GH "https://api.github.com/repos/$Org/$Repo/branches/$b/protection"
      if ($prot) { Write-Host "Protected: $b" -ForegroundColor Green }
      else { $summary.branch_protection_failures += $b; Warn "No protection object returned for $b" }
    } catch {
      $summary.branch_protection_failures += $b
      Warn "Branch not protected: $b"
    }
  }
}

# --- Workflow Lint ---
if ($LintWorkflows -and (SafeCount $summary.workflow_files) -gt 0) {
  Write-Section 'Workflow Lint'
  foreach ($entry in $script:workflowEntries) {
    if ($entry.type -ne 'file') { continue }
    $name = $entry.name
    $lint = @{ valid = $true; issues = @() }
    try {
      $raw = $null
      if ($entry.download_url) {
        $raw = (Invoke-WebRequest -Uri $entry.download_url -Headers @{ 'User-Agent' = 'migration-verifier' } -UseBasicParsing).Content
      }
      if (-not $raw) { $lint.valid = $false; $lint.issues += 'empty_content' }
      else {
        if ($raw -notmatch '(?m)^on:\s*') { $lint.valid = $false; $lint.issues += 'missing_on' }
        if ($raw -notmatch '(?m)^jobs:\s*') { $lint.valid = $false; $lint.issues += 'missing_jobs' }
        if ($raw -match '<<<<<<<|>>>>>>>|=======' ) { $lint.valid = $false; $lint.issues += 'merge_conflict_markers' }
      }
    } catch {
      $lint.valid = $false; $lint.issues += 'fetch_failed'
    }
    $summary.workflow_lint[$name] = $lint
    $status = if ($lint.valid) { 'OK' } else { 'FAIL: ' + ($lint.issues -join ',') }
    $color = if ($lint.valid) { 'Green' } else { 'Yellow' }
    Write-Host " - $name => $status" -ForegroundColor $color
  }
}

Write-Section 'Latest Migration Report'
try {
  $pattern = "$ReportPrefix${ReportProject}_${Repo}_*.json" -replace '\*', '*'
  $reportFile = Get-ChildItem -Path (Join-Path (Get-Location) 'migration_reports') -Filter $pattern -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($reportFile) {
    $summary.latest_report_file = $reportFile.Name
    $report = Get-Content $reportFile.FullName -Raw | ConvertFrom-Json
    $summary.report = [ordered]@{
      source_project = $report.source.project
      source_repo    = $report.source.repository
      target_org     = $report.target.organization
      target_repo    = $report.target.repository
      branches_count = $report.migration_statistics.branches_count
      pipelines_count = $report.migration_statistics.pipelines_count
      pipelines_converted = $report.migration_statistics.pipelines_converted
      git_history_migrated = $report.migration_statistics.git_history_migrated
      work_items_count = $report.migration_statistics.work_items_count
      tags_count = $report.migration_statistics.tags_count
    }
    Write-Host "Report: $($reportFile.Name)" -ForegroundColor Green
    if (-not $ExpectedTagCount -and $report.migration_statistics.tags_count) { $summary.expected_tag_count = [int]$report.migration_statistics.tags_count }
  } else {
    Warn 'No migration report file found.'
    $summary.warnings += 'report_missing'
  }
} catch {
  Warn 'Error reading migration report.'
  $summary.warnings += 'report_read_failed'
}

# --- Tags Enumeration (after report so auto-detect can leverage stats) ---
Write-Section 'Tags'
try {
  $allTags = @()
  for ($page=1; $page -le $MaxTagPages; $page++) {
    $t = Invoke-GH "https://api.github.com/repos/$Org/$Repo/tags?per_page=100&page=$page"
    $tCount = SafeCount $t
    if (-not $t -or $tCount -eq 0) { break }
    $allTags += $t
    if ($tCount -lt 100) { break }
  }
  $summary.tag_count = (SafeCount $allTags)
  if ($ExpectedTagCount) { $summary.expected_tag_count = $ExpectedTagCount }
  if ($null -ne $summary.expected_tag_count) { $summary.tags_match_expected = ($summary.tag_count -eq $summary.expected_tag_count) }
  Write-Host "Tags discovered: $($summary.tag_count)" -ForegroundColor Green
  if ($summary.tags_match_expected -eq $false) { Warn "Tag count mismatch (expected=$($summary.expected_tag_count) actual=$($summary.tag_count))" }
} catch {
  Warn 'Failed to enumerate tags.'; $summary.warnings += 'tags_list_failed'
}

Write-Section 'Summary'

# Shared evaluation block
$failureReasons = @()
$bpFailuresCount = (SafeCount $summary.branch_protection_failures)
if ($summary.workflow_lint -and ($summary.workflow_lint.GetType().GetMethod('GetEnumerator'))) {
  $lintFailuresCount = (SafeCount (@($summary.workflow_lint.GetEnumerator()) | Where-Object { -not $_.Value.valid }))
} else { $lintFailuresCount = 0 }
if (-not $summary.repository_found) { $failureReasons += 'repository_inaccessible' }
if ($FailOnBranchProtection -and $bpFailuresCount -gt 0) { $failureReasons += 'branch_protection' }
if ($FailOnLintErrors -and $lintFailuresCount -gt 0) { $failureReasons += 'workflow_lint' }
if ($FailOnTagMismatch -and $summary.tags_match_expected -eq $false) { $failureReasons += 'tag_mismatch' }
if ($WarnInsteadOfFail -and ((SafeCount $failureReasons) -gt 0)) {
  foreach ($r in $failureReasons) { $summary.warnings += "auto_downgraded_$r" }
  $failureReasons = @()
}
$warningsCount = (SafeCount $summary.warnings)

function Emit-HumanSummary {
  function _rf($name) { if ($summary.report -and $summary.report.Contains($name)) { return $summary.report[$name] } else { return $null } }
  Write-Host "`n=== Compact Summary ===" -ForegroundColor Cyan
  $rows = @(
    @{K='Repo';V="$Org/$Repo"}
    @{K='Repo Found';V=$summary.repository_found}
    @{K='Default Branch';V=$summary.default_branch}
    @{K='Branches';V=$summary.branch_count}
    @{K='Workflow Files';V=($summary.workflow_files -join ', ')}
    @{K='Workflow Runs';V=$summary.workflow_run_count}
    @{K='Last Run';V=$summary.last_workflow_run}
    @{K='Last Conclusion';V=$summary.last_workflow_conclusion}
    @{K='Last Run Age (min)';V=$summary.last_workflow_age_minutes}
    @{K='Report File';V=$summary.latest_report_file}
    @{K='Pipelines Converted';V=(_rf 'pipelines_converted')}
    @{K='Git History Migrated';V=(_rf 'git_history_migrated')}
    @{K='Work Items Count';V=(_rf 'work_items_count')}
    @{K='ADO Variable Groups';V=($summary.ado_variable_groups -join ', ')}
    @{K='ADO Variables (count)';V=(SafeCount $summary.ado_variables)}
    @{K='ADO Service Connections';V=($summary.ado_service_connections -join ', ')}
    @{K='Branch Protection Failures';V=($summary.branch_protection_failures -join ', ')}
    @{K='Tag Count';V=$summary.tag_count}
    @{K='Expected Tag Count';V=$summary.expected_tag_count}
    @{K='Tags Match Expected';V=$summary.tags_match_expected}
    @{K='Workflow Lint Errors';V=((@($summary.workflow_lint.GetEnumerator()) | Where-Object { -not $_.Value.valid } | ForEach-Object { $_.Key } | Sort-Object) -join ', ')}
  )
  $rows | ForEach-Object { "{0,-28} {1}" -f $_.K, $_.V } | Write-Host
  if ($warningsCount -gt 0) { Write-Host "Warnings: $(@($summary.warnings) -join ', ')" -ForegroundColor Yellow }
  return $rows
}

function Compute-ExitCode {
  param([array]$Reasons,[int]$Warns,[bool]$RepoFound)
  if ((SafeCount $Reasons) -gt 0) { return 3 }
  if ($Warns -gt 0) { return ($RepoFound ? 2 : 3) }
  return 0
}

if ($SummaryFile) { try { $summary | ConvertTo-Json -Depth 12 | Out-File -FilePath $SummaryFile -Encoding UTF8 } catch { Warn "Failed to write summary file: $SummaryFile" } }

if ($Json) {
  $exit = Compute-ExitCode -Reasons $failureReasons -Warns $warningsCount -RepoFound $summary.repository_found
  $summary.exit_code = $exit
  $summary | ConvertTo-Json -Depth 12
  if ($TextReportFile) {
    try {
      $lines = @('Migration Verification Report (JSON mode)','')
      foreach ($k in $summary.Keys) {
        $v = $summary[$k]
        if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $v = ($v -join ', ') }
        $lines += ("{0}: {1}" -f $k,$v)
      }
      if ($warningsCount -gt 0) { $lines += "Warnings: $(@($summary.warnings) -join ', ')" }
      if ((SafeCount $failureReasons) -gt 0) { $lines += "Failures: $($failureReasons -join ', ')" }
      $lines | Out-File -FilePath $TextReportFile -Encoding UTF8
    } catch { Warn "Failed to write text report: $TextReportFile" }
  }
  exit $exit
} else {
  $rows = Emit-HumanSummary
  if ($TextReportFile) {
    try {
      $lines = @('Migration Verification Report','')
      foreach ($row in $rows) { $lines += ("{0}: {1}" -f $row.K,$row.V) }
      if ($warningsCount -gt 0) { $lines += "Warnings: $(@($summary.warnings) -join ', ')" }
      if ((SafeCount $failureReasons) -gt 0) { $lines += "Failures: $($failureReasons -join ', ')" }
      $lines | Out-File -FilePath $TextReportFile -Encoding UTF8
    } catch { Warn "Failed to write text report: $TextReportFile" }
  }
  $exit = Compute-ExitCode -Reasons $failureReasons -Warns $warningsCount -RepoFound $summary.repository_found
  $summary.exit_code = $exit
  if ($exit -eq 0) { Write-Host 'All checks passed.' -ForegroundColor Green }
  elseif ($exit -eq 2) { Write-Host 'Completed with warnings.' -ForegroundColor Yellow }
  else { Write-Host ("Failing due to: {0}" -f ($failureReasons -join ', ')) -ForegroundColor Red }
  exit $exit
}
