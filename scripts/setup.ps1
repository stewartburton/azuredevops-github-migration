<#!
.SYNOPSIS
    Windows / PowerShell setup script for Azure DevOps to GitHub Migration Tool.
.DESCRIPTION
    Mirrors functionality of scripts/setup.sh:
      * Verifies Python >= 3.8 and git
      * Creates or reuses a virtual environment (./venv)
      * Installs project in editable mode (optionally dev extras with -Dev)
      * Copies config/config.template.json -> config/config.json if missing
      * Copies .env.example -> .env if missing
      * Generates sample_migration_plan.json
      * Validates CLI (azuredevops-github-migration --version)
      * Creates convenience migrate.cmd launcher
.PARAMETER Dev
    Install development dependencies (pip install -e .[dev])
.PARAMETER Clean
    Remove venv and generated artifacts before setup
.EXAMPLE
    ./scripts/setup.ps1
.EXAMPLE
    ./scripts/setup.ps1 -Dev
.EXAMPLE
    ./scripts/setup.ps1 -Clean; ./scripts/setup.ps1 -Dev
#>
[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($m){ Write-Host "[INFO ] $m" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "[ OK  ] $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "[WARN ] $m" -ForegroundColor Yellow }
function Write-Err($m){ Write-Host "[FAIL ] $m" -ForegroundColor Red }

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot

if($Clean){
    Write-Info 'Cleaning previous artifacts...'
    Remove-Item -Recurse -Force venv, migration_reports, logs, temp -ErrorAction SilentlyContinue | Out-Null
    Remove-Item migrate.cmd -ErrorAction SilentlyContinue | Out-Null
    Write-Ok 'Cleanup complete.'
}

Write-Host '=== Azure DevOps to GitHub Migration Tool (Windows Setup) ===' -ForegroundColor Magenta

# Python check
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if(-not $pyCmd){
    $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if(-not $pyCmd){ Write-Err 'Python 3.8+ not found in PATH.'; exit 1 }
$verOut = & $pyCmd.Source --version
if($verOut -notmatch 'Python 3\.(8|9|1[0-2])'){ Write-Err "Unsupported Python version: $verOut"; exit 1 }
Write-Ok "Python detected: $verOut"

# Git check
if(-not (Get-Command git -ErrorAction SilentlyContinue)){ Write-Err 'git not found in PATH.'; exit 1 }
Write-Ok (git --version)

# Virtual environment
if(-not (Test-Path venv)){
    Write-Info 'Creating virtual environment (venv)...'
    & $pyCmd.Source -m venv venv
    Write-Ok 'Virtual environment created.'
}else{ Write-Warn 'venv already exists (reusing).' }

# Activate venv (scoped to this script)
$activate = Join-Path $repoRoot 'venv' 'Scripts' 'Activate.ps1'
if(-not (Test-Path $activate)){ Write-Err 'Activation script not found.'; exit 1 }
. $activate
Write-Ok "Activated venv using: $activate"

# Upgrade pip quietly
Write-Info 'Upgrading pip (quiet)...'
python -m pip install --upgrade pip | Out-Null

# Editable install
if($Dev){
    Write-Info 'Installing project in editable mode with dev extras...'
    pip install -e .[dev]
}else{
    Write-Info 'Installing project in editable mode...'
    pip install -e .
}

# Ensure config directory
$newConfigDir = Join-Path $repoRoot 'config'
if(-not (Test-Path $newConfigDir)){ New-Item -ItemType Directory -Path $newConfigDir | Out-Null }

# Copy config template
$template = Join-Path $newConfigDir 'config.template.json'
$target   = Join-Path $newConfigDir 'config.json'
if((Test-Path $template) -and -not (Test-Path $target)){
    Copy-Item $template $target
    Write-Ok 'Copied config/config.template.json -> config/config.json'
}else{ Write-Warn 'config/config.json exists or template missing (skipping copy).' }

# Copy .env
$envExample = Join-Path $repoRoot '.env.example'
$envFile    = Join-Path $repoRoot '.env'
if((Test-Path $envExample) -and -not (Test-Path $envFile)){
    Copy-Item $envExample $envFile
    Write-Ok 'Copied .env.example -> .env'
}else{ Write-Warn '.env already exists or example missing (skipping).' }

# Create baseline directories
foreach($d in 'migration_reports','logs','temp'){
    if(-not (Test-Path $d)){ New-Item -ItemType Directory -Path $d | Out-Null }
}

# Sample migration plan
$plan = Join-Path $repoRoot 'sample_migration_plan.json'
if(-not (Test-Path $plan)){
        $planJson = @'
{
    "migrations": [
        {
            "azure_devops": { "project": "YourProjectName", "repository": "your-repo-name" },
            "github": { "repository": "migrated-repo-name", "organization": "your-github-org" },
            "options": { "migrate_work_items": true, "migrate_branches": true, "create_private": true }
        }
    ]
}
'@
        $planJson | Out-File -FilePath $plan -Encoding utf8 -Force
        Write-Ok 'Created sample_migration_plan.json'
}else{ Write-Warn 'sample_migration_plan.json already exists.' }

# Validate CLI
Write-Info 'Validating CLI...'
$cliVer = (azuredevops-github-migration --version 2>$null)
if($LASTEXITCODE -ne 0){ Write-Err 'CLI failed to execute.'; exit 1 }
Write-Ok $cliVer

# Create migrate.cmd convenience wrapper
if(-not (Test-Path (Join-Path $repoRoot 'migrate.cmd'))){
    $wrapper = @'
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" call "%SCRIPT_DIR%venv\Scripts\activate.bat"
azuredevops-github-migration migrate %*
'@
    $wrapper | Out-File -FilePath (Join-Path $repoRoot 'migrate.cmd') -Encoding ascii -Force
    Write-Ok 'Created migrate.cmd wrapper.'
} else { Write-Warn 'migrate.cmd already exists (skipping).' }

# Create azuredevops-github-migration.cmd root wrapper (full CLI access)
if(-not (Test-Path (Join-Path $repoRoot 'azuredevops-github-migration.cmd'))){
    $fullWrapper = @'
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" call "%SCRIPT_DIR%venv\Scripts\activate.bat"
azuredevops-github-migration %*
'@
    $fullWrapper | Out-File -FilePath (Join-Path $repoRoot 'azuredevops-github-migration.cmd') -Encoding ascii -Force
    Write-Ok 'Created azuredevops-github-migration.cmd wrapper.'
} else { Write-Warn 'azuredevops-github-migration.cmd already exists (skipping).' }

Write-Host ''
Write-Host 'Next Steps:' -ForegroundColor Cyan
Write-Host '  1. Edit config/config.json' -ForegroundColor Gray
Write-Host '  2. Edit .env with AZURE_DEVOPS_PAT and GITHUB_TOKEN' -ForegroundColor Gray
Write-Host '  3. Run: azuredevops-github-migration analyze --create-plan --config config/config.json' -ForegroundColor Gray
Write-Host ''
Write-Host 'Happy migrating! 🚀' -ForegroundColor Green

Pop-Location
