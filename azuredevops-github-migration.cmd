@echo off
REM Wrapper to run main CLI inside local venv if present
SETLOCAL ENABLEDELAYEDEXPANSION
SET VENV_DIR=%~dp0venv
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
  CALL "%VENV_DIR%\Scripts\activate.bat"
) ELSE (
  echo [WARN] venv not found at %VENV_DIR% - attempting global install
)
azuredevops-github-migration %*
ENDLOCAL
