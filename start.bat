@echo off
:: Double-click this file to start all services (Backend, Celery, Frontend).
:: Each service opens in its own terminal window.

cd /d "%~dp0"
powershell -File "scripts\start_all.ps1"
