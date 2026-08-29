@echo off
cd /d "%~dp0"
"Expedite.exe" --diagnostic
if errorlevel 1 pause
