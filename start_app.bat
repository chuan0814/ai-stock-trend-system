@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_app.ps1"
if errorlevel 1 pause
endlocal
