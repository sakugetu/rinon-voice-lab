# Rinon Voice Lab

Local prototype chat app that connects LM Studio, Irodori-TTS VoiceDesign, and a simple animated character UI.

Installed app folder: `H:\AI\RinonVoiceLab`

## Assumptions

- LM Studio OpenAI-compatible API: `http://127.0.0.1:1234/v1`
- Irodori-TTS install: `H:\AI\Irodori-TTS`
- Default model: `gemma-4-31b-it`
- App URL: `http://127.0.0.1:7862/`

## Run

No extra Python packages are required by this wrapper app itself. Use the
existing Irodori-TTS virtual environment:

```powershell
cd /d H:\AI\RinonVoiceLab
H:\AI\Irodori-TTS\.venv\Scripts\python.exe app.py
```

Or double-click `start_chat_uv.bat`. If `H:\AI\Irodori-TTS` does not exist yet,
the launcher runs `tools\install_irodori_tts.ps1` first and installs Irodori-TTS.

Manual Irodori-TTS install:

```powershell
cd /d H:\AI\RinonVoiceLab
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1
```

The installer defaults to NVIDIA/CUDA wheels through `uv sync --extra cu128`.
For CPU-only setup:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1 -TorchExtra cpu
```

For documentation completeness:

```powershell
pip install -r requirements.txt
```

## Notes

- Generated temporary audio is written to `static/generated/` and ignored by Git.
- Saved audio is written to `saved_audio/` and ignored by Git.
- Chat/session saves are local runtime data and ignored by Git.
