# Rinon Voice Lab

Rinon Voice Lab is a local Windows prototype that connects:

- LM Studio OpenAI-compatible chat
- Irodori-TTS VoiceDesign speech generation
- a simple animated character UI with editable character profiles

The app is designed to run from any install folder. It does not require a fixed
drive such as `H:`. By default, Irodori-TTS is installed next to this app:

```text
SomeFolder\
  RinonVoiceLab\
  Irodori-TTS\
```

## Requirements

- Windows 10/11
- Git for Windows
- LM Studio with the local server enabled
- A local chat model loaded in LM Studio
- NVIDIA GPU strongly recommended for Irodori-TTS

The app wrapper itself uses only the Python standard library. Irodori-TTS has
its own Python environment and model dependencies.

## Quick Start

1. Clone or download this repository.
2. Start LM Studio and enable the OpenAI-compatible local server.
3. Load a chat model, for example a Gemma instruction model.
4. Double-click `start_chat_uv.bat`.
5. Open `http://127.0.0.1:7862/`.

If Irodori-TTS is not installed yet, `start_chat_uv.bat` runs
`tools\install_irodori_tts.ps1` automatically. The first install can take a long
time because PyTorch and model dependencies are large.

## Manual Irodori-TTS Install

Run this from the app folder:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1
```

The installer defaults to CUDA 12.8 wheels:

```powershell
uv sync --extra cu128
```

For CPU-only setup:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1 -TorchExtra cpu
```

CPU mode is mainly for testing. Voice generation can be very slow.

## Custom Install Paths

Set `IRODORI_ROOT` before launching if you want Irodori-TTS somewhere else:

```powershell
$env:IRODORI_ROOT = "$HOME\AI\Irodori-TTS"
.\start_chat_uv.bat
```

Useful environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `IRODORI_ROOT` | `..\Irodori-TTS` next to this app | Irodori-TTS checkout and virtual environment |
| `LM_STUDIO_URL` | `http://127.0.0.1:1234/v1` | LM Studio OpenAI-compatible endpoint |
| `LM_STUDIO_MODEL` | `gemma-4-31b-it` | Preferred model name |
| `LM_STUDIO_CONTEXT_LIMIT` | `8200` | Visible context budget |
| `IRODORI_TORCH_EXTRA` | `cu128` | Installer torch extra: `cu128`, `cpu`, `rocm`, or `xpu` |

## Character Data

Characters live under `Character\<character-id>\`.

Each character folder can contain:

- `profile.txt` for hand editing
- `profile.json` for structured save/load
- `reference\` for voice reference audio
- `expressions\<slot>\` for expression images

Use the Options dialog in the app to edit character names, prompts, TTS
captions, reference audio, and expression images.

## Optional 2P Remote TTS

By default, both 1P and 2P voices are generated on the local Irodori-TTS
environment.

Advanced users can run 2P TTS on a second Windows machine, for example a 4090
workstation. Configure these variables only if you have that second machine:

| Variable | Purpose |
| --- | --- |
| `LUVIA_REMOTE_TTS_URL` | HTTP server URL for `tools\remote_luvia_tts_server.py` |
| `LUVIA_REMOTE_TTS_HOST` | SSH target used by CLI fallback |
| `LUVIA_REMOTE_IRODORI_ROOT` | Irodori-TTS path on the remote machine |
| `LUVIA_REMOTE_REF_WAV` | Reference wav path on the remote machine |

Footnote: the 4090 path is optional. A normal single-PC setup does not need a
second machine; it will use local TTS for both characters.

## Runtime Files

These are local runtime files and are ignored by Git:

- `logs/`
- `profiles/`
- `saved_audio/`
- `static/generated/`
- Python caches and virtual environments

## Validation

Useful development checks:

```powershell
node --check static\app.js
$env:PYTHONDONTWRITEBYTECODE='1'
..\Irodori-TTS\.venv\Scripts\python.exe -m py_compile app.py tools\remote_luvia_tts_server.py
```
