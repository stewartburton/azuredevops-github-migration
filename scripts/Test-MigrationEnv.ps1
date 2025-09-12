<#!
.SYNOPSIS
  Audit and optionally load required Azure DevOps → GitHub migration environment variables.

.DESCRIPTION
  Reads a .env file (default: ./ .env) and checks for the presence of the required variables
  in both the file and the current PowerShell session (Process scope):
    - AZURE_DEVOPS_PAT
    - GITHUB_TOKEN
    - AZURE_DEVOPS_ORGANIZATION (or legacy AZURE_DEVOPS_ORG)
    - GITHUB_ORGANIZATION      (or legacy GITHUB_ORG)

  Optionally loads them into the current session (Process scope) with -Load and can overwrite
  existing values with -Overwrite. Outputs either a formatted table (default) or JSON (-Json).
  Will return a non‑zero exit code (2) if -FailOnMissing is specified and any required variable
  is absent from the session after optional loading.

.PARAMETER Path
  Path to the .env file. Default: .env in the current working directory.

.PARAMETER Load
  Load variables from the .env file into the current session (Process scope) if not already set.

.PARAMETER Overwrite
  When used with -Load, overwrite any existing session values.

.PARAMETER Json
  Emit machine‑readable JSON instead of a human table.

.PARAMETER FailOnMissing
  Return exit code 2 if any required variable is still missing from the session after loading.

.PARAMETER Quiet
  Suppress non‑error console output (ignored if -Json is used).

.EXAMPLE
  pwsh -File scripts/Test-MigrationEnv.ps1

.EXAMPLE
  pwsh -File scripts/Test-MigrationEnv.ps1 -Load -FailOnMissing

.EXAMPLE
  pwsh -File scripts/Test-MigrationEnv.ps1 -Json | ConvertFrom-Json

.NOTES
  Secrets are masked in output (first 4 + last 4 chars only). Do not commit real secret values.
#>
[CmdletBinding()] param(
  [Parameter(Position=0)]
  [ValidateNotNullOrEmpty()]
  [string]$Path = '.env',

  [Parameter()] [switch]$Load,
  [Parameter()] [switch]$Overwrite,
  [Parameter()] [switch]$Json,
  [Parameter()] [switch]$FailOnMissing,
  [Parameter()] [switch]$Quiet
)

function MaskValue {
  [CmdletBinding()] param([Parameter(Mandatory)][AllowNull()][string]$Value)
  if (-not $Value) { return '' }
  if ($Value.Length -le 8) { return '****' }
  return ($Value.Substring(0,4) + '...' + $Value.Substring($Value.Length - 4))
}

if (-not (Test-Path -LiteralPath $Path)) {
  Write-Error "Env file not found: $Path"
  if ($FailOnMissing) { $global:LASTEXITCODE = 2 } else { $global:LASTEXITCODE = 0 }
  return
}

# Parse .env
$fileMap = @{}
Get-Content -LiteralPath $Path | ForEach-Object {
  $l = $_
  if ($l -match '^[ \t]*#') { return }
  if ($l.Trim().Length -eq 0) { return }
  if ($l -match '^[ \t]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
    $k = $matches[1].Trim()
    $v = $matches[2].Trim()
    if ($v.Length -ge 2) {
      $f = $v[0]; $e = $v[$v.Length-1]
      if ( ($f -eq '"' -and $e -eq '"') -or ($f -eq "'" -and $e -eq "'") ) { $v = $v.Substring(1,$v.Length-2) }
    }
    $fileMap[$k] = $v
  }
}

$required = @('AZURE_DEVOPS_PAT','GITHUB_TOKEN','AZURE_DEVOPS_ORGANIZATION','GITHUB_ORGANIZATION')
$aliases = @{
  'AZURE_DEVOPS_PAT' = @('AZURE_DEVOPS_PAT')
  'GITHUB_TOKEN' = @('GITHUB_TOKEN')
  'AZURE_DEVOPS_ORGANIZATION' = @('AZURE_DEVOPS_ORGANIZATION','AZURE_DEVOPS_ORG')
  'GITHUB_ORGANIZATION' = @('GITHUB_ORGANIZATION','GITHUB_ORG')
}

if ($Load) {
  foreach ($r in $required) {
    $current = [Environment]::GetEnvironmentVariable($r,'Process')
    if ($current -and -not $Overwrite) { continue }
    foreach ($a in $aliases[$r]) {
      if ($fileMap.ContainsKey($a)) { [Environment]::SetEnvironmentVariable($r,$fileMap[$a],'Process'); break }
    }
  }
}

$results = @()
foreach ($r in $required) {
  $presentFile = $false; $fileVal = $null
  foreach ($a in $aliases[$r]) { if ($fileMap.ContainsKey($a)) { $presentFile = $true; $fileVal = $fileMap[$a]; break } }
  $sessionVal = [Environment]::GetEnvironmentVariable($r,'Process')
  $props = @{ Name = $r; InFile = $presentFile; InSession = ([string]::IsNullOrEmpty($sessionVal) -eq $false); FileMasked = if ($presentFile) { MaskValue $fileVal } else { '' }; SessionMasked = if ($sessionVal) { MaskValue $sessionVal } else { '' }; Matches = ($sessionVal -and $fileVal -and $sessionVal -eq $fileVal) }
  $results += (New-Object PSObject -Property $props)
}

$missing = $results | Where-Object { -not $_.InSession }

if ($Json) {
  $obj = [PSCustomObject]@{
    path       = (Resolve-Path -LiteralPath $Path).Path
    loaded     = [bool]$Load
    overwrite  = [bool]$Overwrite
    ok         = ($missing.Count -eq 0)
    missing    = $missing.Name
    variables  = $results
    timestamp  = (Get-Date).ToString('o')
  }
  $obj | ConvertTo-Json -Depth 4
} else {
  if (-not $Quiet) {
    Write-Host "Environment audit: $(Resolve-Path -LiteralPath $Path)" -ForegroundColor Cyan
    $results | Sort-Object Name | Format-Table Name,InFile,InSession,FileMasked,SessionMasked,Matches -AutoSize
    if ($missing) {
      Write-Host "Missing (not in session): $($missing.Name -join ', ')" -ForegroundColor Yellow
    } else {
      Write-Host "All required variables are present." -ForegroundColor Green
    }
  }
}

if ($FailOnMissing -and $missing) { $global:LASTEXITCODE = 2 } else { $global:LASTEXITCODE = 0 }
return
