@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\start_cx.ps1 %*
if errorlevel 1 (
  echo CX startup failed. See docs\CX_SETUP.md and the error above.
  pause
  exit /b 1
)
