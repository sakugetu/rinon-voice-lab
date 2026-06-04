@echo off
setlocal
cd /d "%~dp0"
if "%IRODORI_ROOT%"=="" set "IRODORI_ROOT=%~dp0..\Irodori-TTS"
for %%I in ("%IRODORI_ROOT%") do set "IRODORI_ROOT=%%~fI"
if not exist "%IRODORI_ROOT%\.venv\Scripts\python.exe" (
  echo Irodori-TTS was not found at "%IRODORI_ROOT%".
  echo Installing Irodori-TTS. This may take a while.
  powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0tools\install_irodori_tts.ps1" -IrodoriRoot "%IRODORI_ROOT%"
  if errorlevel 1 exit /b %errorlevel%
)
"%IRODORI_ROOT%\.venv\Scripts\python.exe" app.py
