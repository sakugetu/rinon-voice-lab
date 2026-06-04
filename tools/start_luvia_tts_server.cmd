@echo off
setlocal
if "%IRODORI_ROOT%"=="" set "IRODORI_ROOT=%~dp0..\..\Irodori-TTS"
for %%I in ("%IRODORI_ROOT%") do set "IRODORI_ROOT=%%~fI"
cd /d "%IRODORI_ROOT%"
if not exist outputs mkdir outputs
"%IRODORI_ROOT%\.venv\Scripts\python.exe" "%~dp0remote_luvia_tts_server.py" >> "%IRODORI_ROOT%\outputs\remote_luvia_server.out.log" 2>> "%IRODORI_ROOT%\outputs\remote_luvia_server.err.log"
