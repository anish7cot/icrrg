@echo off
:: Double-click this file to set up the entire project.
:: It launches the PowerShell setup script automatically.

cd /d "%~dp0"
powershell -File "scripts\setup.ps1"
pause
