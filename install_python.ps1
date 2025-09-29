<#!
.SYNOPSIS
  Bootstraps a local Python 3.12 environment for this repository on Windows (VS Code friendly).
.DESCRIPTION
  - Installs Python via winget if neither `python` nor `py` is available.
  - Resolves a concrete python.exe (prefers installed path over Store alias).
  - Creates a virtual environment `venv` (idempotent).
  - Activates the venv in the current shell.
  - Upgrades pip and installs the project in editable mode (`pip install -e .`).
  - Prints versions and success status.

  Re-run safely: existing venv is reused.

.PARAMETER PythonWingetId
  Winget package identifier for Python (default: Python.Python.3.12).
.PARAMETER VenvDir
  Virtual environment directory (default: venv).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install_python.ps1

.EXAMPLE
  .\install_python.ps1 -PythonWingetId Python.Python.3.11 -VenvDir .venv

.NOTES
  Requires winget (Windows 10+ with App Installer) for auto-install path. If winget is unavailable,
  the script will abort with guidance.
#>
param(
  [string]$PythonWingetId = 'Python.Python.3.12',
  [string]$VenvDir = 'venv'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg){ Write-Host "[INFO] $msg" }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err ($msg){ Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Info "Starting Python bootstrap (winget ID = $PythonWingetId, venv=$VenvDir)"

# 1. Install Python if neither python nor py is present
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Info "Python not detected. Installing via winget..."
    winget install -e --id $PythonWingetId --accept-package-agreements --accept-source-agreements | Out-Null
    Write-Info "winget install attempted. PATH may require a new terminal if python is still absent."
  } else {
    Write-Err "winget not found. Install Python manually from https://www.python.org/downloads/windows/ then re-run." 
    exit 1
  }
}

# 2. Resolve python executable
$pythonExe = $null
# Expected standard local install root
$expectedDir = Join-Path $env:LOCALAPPDATA 'Programs/Python'
if (Test-Path $expectedDir) {
  $candidates = Get-ChildItem $expectedDir -Directory | Where-Object { $_.Name -match '^Python3' } | Sort-Object LastWriteTime -Descending
  if ($candidates) {
    $maybe = Join-Path $candidates[0].FullName 'python.exe'
    if (Test-Path $maybe) { $pythonExe = $maybe }
  }
}

# Fallback to PATH python
if (-not $pythonExe) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { $pythonExe = $cmd.Source }
}

# Fallback to py launcher attempt
if (-not $pythonExe) {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $env:PYLAUNCHER_ALLOW_INSTALL = '1'
    try { py -3.12 -V | Out-Null } catch {}
    $cmd2 = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd2) { $pythonExe = $cmd2.Source }
  }
}

if (-not $pythonExe) {
  Write-Err "Could not resolve a python.exe. Close VS Code terminal and re-run, or validate installation."
  exit 1
}
Write-Info "Using Python: $pythonExe"

# 3. Create virtual environment
if (-not (Test-Path $VenvDir)) {
  Write-Info "Creating virtual environment '$VenvDir'..."
  & $pythonExe -m venv $VenvDir
  if ($LASTEXITCODE -ne 0) { Write-Err "venv creation failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
} else {
  Write-Info "Virtual environment '$VenvDir' already exists; reusing."
}

# 4. Activate
$activateScript = Join-Path $VenvDir 'Scripts/Activate.ps1'
if (-not (Test-Path $activateScript)) { Write-Err "Activation script missing: $activateScript"; exit 1 }
Write-Info "Activating venv..."
. $activateScript

# 5. Upgrade pip and install project
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip | Out-Null

Write-Info "Installing project (editable)..."
pip install -e . | Out-Null

# 6. Verify
$pyVer = python --version
$pipVer = pip --version
Write-Info "Python: $pyVer"
Write-Info "Pip: $pipVer"
Write-Host "[SUCCESS] Environment ready. To reuse later: . ./$VenvDir/Scripts/Activate.ps1" -ForegroundColor Green
