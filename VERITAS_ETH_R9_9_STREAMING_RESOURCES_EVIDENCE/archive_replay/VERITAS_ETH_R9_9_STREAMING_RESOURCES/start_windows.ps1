# Run from a PowerShell terminal: powershell -ExecutionPolicy Bypass -File .\start_windows.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -e ".[matching]"
& '.\.venv\Scripts\python.exe' -m uvicorn veritas.api.main:app --host 127.0.0.1 --port 8080
