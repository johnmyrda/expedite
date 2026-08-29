@echo off
set "EXPEDITE_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath $env:EXPEDITE_DIR -Recurse -File | Unblock-File"
start "" "%EXPEDITE_DIR%Expedite.exe"
