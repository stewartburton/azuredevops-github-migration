@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" call "%SCRIPT_DIR%venv\Scripts\activate.bat"
azuredevops-github-migration migrate %*
