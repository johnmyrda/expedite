@echo off
set "EXPEDITE_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath $env:EXPEDITE_DIR -Recurse -File | Unblock-File"
cd /d "%EXPEDITE_DIR%"
"Expedite.exe" --diagnostic
if errorlevel 1 pause
