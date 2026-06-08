# Rinon Voice Lab 日本語README

Rinon Voice Lab は、LM Studio のローカルLLMと Irodori-TTS をつないで、キャラクター会話と音声読み上げを行うローカルアプリです。主な確認環境は Windows ですが、macOS では実験的に起動できるようにしています。

主な機能:

- LM Studio の OpenAI互換ローカルAPIと連携
- Irodori-TTS VoiceDesign による日本語音声生成
- 1P/2P キャラクターの設定、名前、TTS Caption、表情画像を編集
- 会話ログ、セッション、キャラクターデータの保存と読み込み
- 簡易Web検索メモをLLMプロンプトへ追加
- 2P音声だけを別PCの Irodori-TTS へ送るリモートTTSモード

## 画面モード

### 1Pモード

1Pモードは、1人のキャラクターと会話しながら、LM Studio の応答を Irodori-TTS で読み上げる基本モードです。キャラ設定、TTS Caption、Web検索、話速、感情スタイルを同じ画面で調整できます。

![Rinon Voice Lab 1Pモード](docs/images/rinon-1p-mode.png)

### 2Pキャラモード

2Pキャラモードでは、1Pと2Pのキャラクターを同じ画面に表示し、二人の会話を交互に進められます。2人だけで話すモード、2P音声の別PC生成、キャラクターごとの設定やTTS Captionにも対応しています。

![Rinon Voice Lab 2Pキャラモード](docs/images/rinon-2p-mode.png)

## サポートについて

このリポジトリは個人の実験的な公開物です。サポート、継続メンテナンス、環境ごとの動作保証、個別の導入支援は期待しないでください。参考実装またはローカル実験用として利用してください。

固定ドライブは前提にしていません。`H:` 以外の場所にも配置できます。標準では、このアプリの隣に Irodori-TTS を置きます。

```text
任意のフォルダ\
  RinonVoiceLab\
  Irodori-TTS\
```

## 必要環境

- Windows 10 / 11
- macOS 14 以降の Apple Silicon Mac（実験的対応）
- Python 3.10 以上
- Git
- LM Studio
- LM Studio 側でローカルサーバーを有効化
- ローカル会話モデル
- Irodori-TTS 用の NVIDIA GPU 推奨
- `uv`

標準モデルは `gemma-4-12b-it` を想定しています。31Bモデルも使えますが、VRAM使用量が大きくなります。

macOS では CUDA は使えません。Irodori-TTS は PyTorch の MPS が使える Apple Silicon Mac では `mps`、それ以外では `cpu` で動きます。MPS/CPU では Irodori-TTS の `bf16` は使えないため、`fp32` を使います。音声生成は NVIDIA GPU 環境より遅くなる可能性があります。

Rinon Voice Lab 本体は Python 標準ライブラリだけで動きます。そのため、`requirements.txt` にはアプリ本体用の追加パッケージはありません。Irodori-TTS の依存関係は、Irodori-TTS 専用の仮想環境へインストールします。

## インストールと起動（Windows）

1. このリポジトリをクローン、またはZIPで展開します。
2. LM Studio を起動します。
3. LM Studio の Local Server を有効にします。
4. `gemma-4-12b-it` などの会話モデルを読み込みます。
5. `start_chat_uv.bat` をダブルクリックします。
6. ブラウザで `http://127.0.0.1:7862/` を開きます。

Irodori-TTS が未インストールの場合、`start_chat_uv.bat` が `tools\install_irodori_tts.ps1` を自動実行します。初回は PyTorch やTTSモデルの依存関係が大きいため、時間がかかります。

## インストールと起動（macOS）

1. LM Studio を起動します。
2. LM Studio の Local Server を有効にします。
3. 会話モデルを読み込みます。
4. Terminal でこのリポジトリに移動します。
5. 次を実行します。

```bash
chmod +x start_chat_mac.sh tools/install_irodori_tts.sh
./start_chat_mac.sh
```

6. ブラウザで `http://127.0.0.1:7862/` を開きます。

`start_chat_mac.sh` は、Irodori-TTS が未インストールなら `tools/install_irodori_tts.sh` を実行します。macOS では `uv sync --extra cpu` を使います。この extra は macOS では標準の PyPI PyTorch wheel を使うため、Apple Silicon では MPS が有効な PyTorch であれば `IRODORI_MODEL_DEVICE=auto` によって `mps` が選ばれます。

Python 3.14 では PyTorch wheel が揃わない可能性があるため、macOS スクリプトは標準で Python 3.10 を使います。変更したい場合は次のように指定します。

```bash
IRODORI_PYTHON_VERSION=3.13 ./start_chat_mac.sh
```

Irodori-TTS をアプリの隣以外に置きたい場合:

```bash
IRODORI_ROOT="$PWD/.deps/Irodori-TTS" ./start_chat_mac.sh
```

## Irodori-TTS の手動インストール

アプリフォルダで次を実行します。

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1
```

標準では CUDA 12.8 用の依存関係を入れます。

```powershell
uv sync --extra cu128
```

CPUだけで試す場合:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_irodori_tts.ps1 -TorchExtra cpu
```

CPUモードは動作確認用です。音声生成はかなり遅くなる可能性があります。

macOS で手動インストールする場合:

```bash
IRODORI_TORCH_EXTRA=cpu tools/install_irodori_tts.sh
```

## requirements.txt について

`requirements.txt` は、Rinon Voice Lab 本体に直接必要なPythonパッケージがないことを示すためのファイルです。

Irodori-TTS の依存関係は次のどちらかで入れてください。

- `start_chat_uv.bat` から自動インストール
- `tools\install_irodori_tts.ps1` を手動実行

`pip install -r requirements.txt` だけでは Irodori-TTS は入りません。

## 設定

主な環境変数:

| 変数 | 標準値 | 内容 |
| --- | --- | --- |
| `IRODORI_ROOT` | アプリ隣の `..\Irodori-TTS` | Irodori-TTS の場所 |
| `LM_STUDIO_URL` | `http://127.0.0.1:1234/v1` | LM Studio の OpenAI互換API |
| `LM_STUDIO_MODEL` | `gemma-4-12b-it` | 優先モデル名 |
| `LM_STUDIO_CONTEXT_LIMIT` | `8200` | 表示上のコンテキスト上限 |
| `IRODORI_TORCH_EXTRA` | `cu128` | Irodori-TTS インストール時の torch extra |
| `IRODORI_MODEL_DEVICE` | `auto` | Irodori-TTS のモデル実行デバイス。`auto`, `cuda`, `mps`, `cpu`, `xpu` |
| `IRODORI_MODEL_PRECISION` | `auto` | モデル精度。`auto`, `fp32`, `bf16` |
| `IRODORI_CODEC_DEVICE` | `auto` | codec 実行デバイス。通常はモデルと同じ |
| `IRODORI_CODEC_PRECISION` | `auto` | codec 精度。macOS では `fp32` |

## キャラクターデータ

キャラクターは `Character\<character-id>\` の下で管理します。

各キャラクターフォルダには、次のようなファイルやフォルダを置けます。

- `profile.txt`: 手で編集しやすい設定ファイル
- `profile.json`: アプリの保存/読み込み用データ
- `reference\`: 参考音声
- `expressions\<slot>\`: 表情ごとの画像

アプリの `Options` 画面から、キャラ名、キャラ設定、TTS Caption、参考音声、表情画像を編集できます。

## 2PリモートTTS

通常は、1P/2Pの音声を同じPCの Irodori-TTS で生成します。

ツールバーの `TTS PC` で次を選べます。

- `1 PC`: 1P/2Pの音声をこのPCで生成
- `2 PCs`: 1PはこのPC、2Pだけを別PCへ送信

`2 PCs` を選んだ場合は、`2P IP` に2台目のPCを入力します。

例:

- `192.168.0.10`
- `192.168.0.10:7874`
- `http://192.168.0.10:7874`

2台目のWindows PCでは、次のようにリモートTTSサーバーを起動します。

```powershell
$env:IRODORI_ROOT = "H:\AI\Irodori-TTS"
$env:LUVIA_SERVER_PORT = "7874"
python tools\remote_luvia_tts_server.py
```

2台目にも Irodori-TTS がインストールされていて、メインPCからアクセスできる必要があります。

macOS や Linux でリモートTTSサーバーを起動する場合:

```bash
IRODORI_ROOT="$PWD/../Irodori-TTS" \
LUVIA_SERVER_PORT=7874 \
IRODORI_MODEL_DEVICE=auto \
python tools/remote_luvia_tts_server.py
```

## 外部Speakモード

Codex、Claude Code、または別のローカルツールから短いテキストを送り、開いている Rinon Voice Lab のキャラクターUIで読み上げられます。

Rinon Voice Lab を起動して `http://127.0.0.1:7862/` を開いたあと、UTF-8 JSONをPOSTします。

```powershell
$body = @{
  text = "リノンから外部スピークのテストだよ。"
  emoji = "🤭"
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

主な項目:

| 項目 | 内容 |
| --- | --- |
| `text` | 読み上げるテキスト |
| `emoji` / `emojiStyle` | Irodori の感情絵文字 |
| `caption` / `ttsCaption` | VoiceDesign の演技キャプション |
| `speakerSlot` | `main` または `second` |
| `referencePath` | 任意の参考音声パス |
| `steps` | Irodori の生成ステップ数 |
| `speechRate` | `normal` または `fast` |

ブラウザ側は `/api/speak-events` を監視し、新しいイベントを通常のキャラクターアニメーション、表情切り替え、左右パン、音声保存機能つきで再生します。

## 配布前に消してよい実行時ファイル

次のフォルダはローカル実行時に作られるため、Gitでは無視しています。

- `logs/`
- `profiles/`
- `saved_audio/`
- `static/generated/`
- `__pycache__/`
- `.venv/`

## 動作確認

開発時の簡易チェック:

```powershell
node --check static\app.js
$env:PYTHONDONTWRITEBYTECODE='1'
..\Irodori-TTS\.venv\Scripts\python.exe -B -m py_compile app.py tools\remote_luvia_tts_server.py
```

macOS:

```bash
node --check static/app.js
PYTHONDONTWRITEBYTECODE=1 python3.10 -B -m py_compile app.py tools/remote_luvia_tts_server.py
```

## ライセンス

MIT License です。詳しくは [LICENSE](LICENSE) を参照してください。
