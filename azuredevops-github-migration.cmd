@echo off
REM Windows launcher for azuredevops-github-migration avoiding recursive self-call.
REM This script intentionally invokes the Python module directly instead of calling
REM a same-named shim that may resolve back to this file (causing infinite recursion).

SETLOCAL ENABLEDELAYEDEXPANSION
SET SCRIPT_DIR=%~dp0
SET VENV_PY=%SCRIPT_DIR%venv\Scripts\python.exe
SET FOUND_PY=

IF EXIST "%VENV_PY%" (
  SET "FOUND_PY=%VENV_PY%"
) ELSE (
  REM Try py launcher first
  where py >NUL 2>&1 && (
    py -3 -c "import sys;print(sys.executable)" >NUL 2>&1 && SET "FOUND_PY=py -3"
  )
  IF NOT DEFINED FOUND_PY (
    where python >NUL 2>&1 && SET "FOUND_PY=python"
  )
)

IF NOT DEFINED FOUND_PY (
  echo [ERROR] Could not locate Python interpreter. Ensure Python is in PATH or create venv at %SCRIPT_DIR%venv.
  EXIT /B 1
)

REM Execute module with all forwarded arguments.
%FOUND_PY% -m azuredevops_github_migration %*
SET RC=%ERRORLEVEL%
ENDLOCAL & EXIT /B %RC%
