# DAIV CX 専用モード

CXでの構成は「音声モデル: AMD GPU / BF16」「音声復元: CPU / FP32」「電子透かし: OFF」です。
既存のNVIDIA CUDA、CPU、macOSの起動経路はStandardとして残しています。
CXではROCm版PyTorchのAPI名が `cuda` になるため、状態表示の `cuda` はNVIDIAを意味しません。

## 起動

1. 下記の初回登録を済ませます。
2. `start_chat.bat` を開き、`2`（DAIV CX）を選びます。直接 `start_chat_cx.bat` を開いても同じです。
3. ブラウザーで `http://127.0.0.1:7862/` を開きます。音声の自動再生には最初に画面をクリックしてください。
4. 状態欄の `CX / GPU生成・CPU復元 / 透かしOFF` を確認します。
5. LMの選択欄から、LM Studioに既にロードしたモデルを選びます。アプリはLMモデルをロード／アンロードしません。

モードはサーバー起動時に固定します。変更する場合は、そのサーバーのコンソールでCtrl+Cを押して終了し、起動し直してください。
別モードのサーバーを同じポートに重ねて起動しないでください。
Standardは `start_chat.bat` の `1` または従来のランチャーです。Standardの既存環境変数によるCPU/CUDA選択は変更していません。

## 初回登録（今回検証したCX）

本体と音声実行環境を別フォルダーにします。Gitにはモデル、venv、個人設定、会話履歴を入れません。
今回の音声実行環境は既に独立して構築・検証済みです。名前に `experiments` を含みますが、登録後はアプリの依存先なので削除・移動しないでください。

```powershell
git clone --branch codex/cx-gpu-mode https://github.com/sakugetu/rinon-voice-lab.git C:\AI\RinonVoiceLab-CX
Set-Location C:\AI\RinonVoiceLab-CX
powershell -NoProfile -ExecutionPolicy Bypass -File tools\start_cx.ps1 `
  -RuntimeRoot C:\AI\experiments\rvl-cx-gpu-20260926-1849 -Register -Check
.\start_chat_cx.bat
```

既にクローン済みならcloneは繰り返しません。登録時はGPU、独立Python、透かしOFF対応を確認し、成功後に `cx.local.json` を新規作成します。
登録済み設定は自動上書きしません。登録先変更時はバックアップして `runtimeRoot` を編集し、`-Check` と音声テストを実行してください。
PythonをPATHに追加する必要はありません。PowerShellランチャーが登録先のPythonを使用します。

## 実行環境の契約

`runtimeRoot` の中に次のものが必要です。

```text
venv/Scripts/python.exe
source/irodori_tts/                 # 検証済みのIrodori v4.1コード
models/phasefield-audio--Irodori-TTS-v4.1-Anime/model.safetensors
models/Aratako--Semantic-DACVAE-Japanese-32dim/weights.pth
hf-cache/hub/                       # トークナイザー等のオフラインキャッシュ
```

検証構成: Windows、Radeon 8060S、Python 3.12.11、PyTorch 2.9.1+rocm7.2.1、ROCm 7.2.1。
依存パッケージの実測一覧は `cx/requirements-validated.txt` です。別のPython版へのインストール保証はありません。
Irodoriの宣言するtorch>=2.10等に対し、これはWindows向けAMD配布版に合わせた独自固定構成です。
`pip check`の成功だけでIrodoriの全宣言要件に適合したとは扱いません。sourceを通常の依存解決付きでインストールし直すと、この固定構成を崩す可能性があります。
venvには共有環境を参照する `.pth` を追加しません。通常のCUDA版PyTorchやComfyUIの環境に混ぜないでください。

独立したIrodoriコードには次のパッチが必要です。

- `RuntimeKey.watermark_enabled` を追加し、OFF時にはSilentCipherをロードしない。
- Windows ROCmで未提供のdistributed APIが原因となるaudiotoolsのインポートエラーを回避する。

パッチと適用ツールは `cx/`、`tools/patch_cx_runtime.py` に置いています。
新環境の再構築では、既知の動作版のsource・models・キャッシュを新しいフォルダーへコピーし、Python 3.12.11で新規venvを作り、検証済み依存一覧をインストールしてから適用します。
既存venvを別パスへ移動・コピーして再利用する方法は推奨しません。今回の登録作業では再インストールも既存環境の変更も行いません。

```powershell
# 新しい空の環境用の例。元の環境では実行しないでください。
# source / models / hf-cache は既知の動作版から別途コピー済みとします。
uv venv --python 3.12.11 C:\AI\RinonRuntime-next\venv
uv pip install --python C:\AI\RinonRuntime-next\venv\Scripts\python.exe -r cx\requirements-validated.txt
& C:\AI\RinonRuntime-next\venv\Scripts\python.exe tools\patch_cx_runtime.py --runtime-root C:\AI\RinonRuntime-next
uv pip check --python C:\AI\RinonRuntime-next\venv\Scripts\python.exe
```

新規環境の完全な再構築は、この実装の動作確認とは別の受け入れ試験が必要です。
ROCmやIrodoriを無条件に最新版へ更新するコマンドは起動時に実行しません。
CXの起動はオフラインモードで、必要なキャッシュがなければエラーにします。

## 実装上の扱い

CXはGradio画面の内部関数に依存せず、Irodoriの `InferenceRuntime` を直接呼びます。
生成したWAVは従来どおり `/api/speak`、`/api/chat`、画面の音声プレイヤー・保存機能へ渡します。
絵文字の定義はIrodoriソースからリテラルデータだけ読み取り、Gradioをインポートしません。
音声モデルは初回生成時にロードし、その後保持します。複数のTTS要求はロックで直列化します。
このロックはLM Studioの推論を止めるものではなく、外部からLMへ同時入力すればGPU競合は起こり得ます。

CPUへの自動フォールバックはありません。CX用GPUが使えない場合は明示的に失敗します。
両話者をローカル生成する場合は同じCXランタイムを使用します。別ホストへの2P音声送信設定は別経路です。

動作確認: [CX_TESTING.md](CX_TESTING.md)。更新・復旧: [CX_UPDATES.md](CX_UPDATES.md)。
