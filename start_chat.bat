@echo off
setlocal
cd /d "%~dp0"
echo 1. Standard - existing CPU / NVIDIA CUDA / auto settings
echo 2. DAIV CX - AMD GPU synthesis, CPU decode, watermark off
choice /c 12 /n /m "Select mode [1/2]: "
if errorlevel 2 (
  call start_chat_cx.bat
) else (
  set "RINON_MODE=standard"
  call start_chat_uv.bat
)
