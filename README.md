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

## 日本語概要

Rinon Voice Lab は、LM Studio のローカルLLMと Irodori-TTS をつなぐ、
Windows向けのローカル会話・読み上げアプリです。

- 1P/2Pキャラクター会話
- Irodori-TTS VoiceDesign による音声生成
- キャラクター画像、表情差分、参考音声、TTS Caption の管理
- Web検索メモをLLMプロンプトへ差し込む簡易検索機能
- 2P音声だけを別PCのIrodori-TTSへ送るリモートTTSモード

基本モデルは軽量運用を優先して `gemma-4-12b-it` にしています。
31B級モデルも使えますが、A6000でもVRAMを大きく消費します。

### 日本語クイックスタート

1. LM Studioを起動し、OpenAI互換ローカルサーバーを有効にします。
2. `gemma-4-12b-it` などの会話モデルを読み込みます。
3. `start_chat_uv.bat` を実行します。
4. ブラウザで `http://127.0.0.1:7862/` を開きます。

Irodori-TTSが見つからない場合、起動BATが `tools\install_irodori_tts.ps1`
を使って、アプリの隣に `Irodori-TTS` をセットアップします。

### 公開・配布時の注意

`logs/`, `profiles/`, `saved_audio/`, `static/generated/` はローカル実行時の
履歴・設定・生成音声です。Gitには含めない設定にしてありますが、ZIP配布などで
フォルダごと渡す場合は削除してください。

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
| `LM_STUDIO_MODEL` | `gemma-4-12b-it` | Preferred model name |
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

In the main toolbar, use `TTS PC` to choose the runtime mode:

- `1 PC`: generate both 1P and 2P voices on this machine.
- `2 PCs`: generate 1P locally and send only 2P voice generation to a second
  machine.

When `2 PCs` is selected, enter the second machine in `2P IP`. An IP-only value
such as `192.168.0.10` is expanded to `http://192.168.0.10:7874`. You can also
enter `192.168.0.10:7874` or a full URL.

On the second Windows machine, start the lightweight remote TTS server:

```powershell
$env:IRODORI_ROOT = "H:\AI\Irodori-TTS"
$env:LUVIA_SERVER_PORT = "7874"
python tools\remote_luvia_tts_server.py
```

The second machine must have Irodori-TTS installed and reachable from the main
machine. The remote server exposes `/health` and `/synthesize`.

Advanced users can still configure remote 2P TTS through environment variables:

| Variable | Purpose |
| --- | --- |
| `LUVIA_REMOTE_TTS_URL` | HTTP server URL for `tools\remote_luvia_tts_server.py` |
| `LUVIA_REMOTE_DEFAULT_PORT` | Port added when the UI receives an IP-only value, default `7874` |
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

## External Speak Mode

RinonVoiceLab can receive short text from Codex, Claude Code, or another local
tool and speak it through the currently open character UI.

Start RinonVoiceLab, open `http://127.0.0.1:7862/`, then POST:

```powershell
$body = @{
  text = "リノンから外部スピークのテストだよ。"
  emoji = ""
  caption = "soft cheerful Japanese anime voice, clear pronunciation"
  speakerSlot = "main"
  steps = 8
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  http://127.0.0.1:7862/api/speak `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Payload keys:

| Key | Purpose |
| --- | --- |
| `text` | Text to speak |
| `emoji` / `emojiStyle` | Irodori style emoji |
| `caption` / `ttsCaption` | VoiceDesign acting caption |
| `speakerSlot` | `main` or `second` |
| `referencePath` | Optional reference wav path |
| `steps` | Irodori generation steps |
| `speechRate` | `normal` or `fast` |
| `durationScale` | Optional direct duration scale |

The browser polls `/api/speak-events` and plays new external speak events with
the normal character animation, expression switching, panning, and audio save
controls. Refresh the browser after updating the app so the polling code is
loaded.

## Validation

Useful development checks:

```powershell
node --check static\app.js
$env:PYTHONDONTWRITEBYTECODE='1'
..\Irodori-TTS\.venv\Scripts\python.exe -m py_compile app.py tools\remote_luvia_tts_server.py
```

## License

MIT License. See [LICENSE](LICENSE).

## ライセンス

MITライセンスです。詳細は [LICENSE](LICENSE) を参照してください。
