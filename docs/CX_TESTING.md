# CX 動作確認

## 更新ごとの短い確認

1. `tools/start_cx.ps1 -Check` でROCm・Python・パッチの読み込みを確認。
2. `start_chat_cx.bat` で起動し、画面のCXモード表示とLMの選択を確認。
3. 次のスモークテストを実行。既に存在する出力フォルダーには書き込まないため、毎回新しい名前を指定。

```powershell
$python = 'C:\AI\experiments\rvl-cx-gpu-20260926-1849\venv\Scripts\python.exe'
& $python -X utf8 -B tools\smoke_cx.py --output logs\cx-smoke-001 --rounds 2
```

5文を2巡、合計10回のAPI要求を実行します。句点により1要求から複数WAVが生成される場合があります。
チェック内容: HTTP応答、GPU生成／CPU復元／透かしOFFのメタデータ、WAVの完全読み出し・長さ・非無音、画面向け音声イベント。
結果は `status.json`、`run.log`、`results.json`、`environment.json`、WAV、`DONE.txt` に保存。
`DONE.txt`だけで成功とは判定しません。`status.json` の `completed` / `exit_code: 0` と出力を確認します。
エラー時は `BLOCKED.md` を出し、そのテストは停止します。無制限再試行はしません。
状態取得はLM Studioのモデル一覧を読みますが、LMへの会話入力・ロード・アンロードは行いません。

## 手で確認すること

- ブラウザーをクリックして音声再生を許可し、日本語の読み、声質、音切れ、音量、表情、保存・再生を確認。
- LM→返答→TTS→再生という会話を実際に繰り返す。LMの量子化、コンテキスト長、入力文を記録する。
- LMをE4B相当と31Bカスタム量子化で分けて評価。未ロードのモデルを勝手に入れ替えない。
- 20〜30分の連続会話で、返答待ち時間、音声が鳴るまでの時間、Windows空きRAM、ページング、エラーを記録。
- 長文、短文、話速、絵文字、話者切替、停止後の再起動を確認。
- 同時要求は専用の負荷試験で評価する。1人用試験だけで複数利用者の商用運用を保証しない。

APIメタデータの `rssBytes` は生成後のプロセス常駐メモリ、`peakWorkingSetBytes` はWindowsのプロセス最大ワーキングセット、`availableMemoryBytes` はシステム空きRAMです。
`gpuPeakAllocatedBytes` はPyTorchの割当量で、ドライバーや他アプリを含むGPUメモリ全量ではありません。
CXは共有メモリ構成なので、これらを単純合算して物理RAM使用量としないでください。

## 標準モードの回帰確認

```powershell
# リポジトリのルートで実行する。Python版と探索先を明示する。
py -3.11 -X utf8 -B -m unittest discover -s .\tests -v
node --check static/app.js
git diff --check
```

CPU/CUDA/auto設定、CX経路の分離、TTS直列化、異常設定の停止、Gradioなしの絵文字読込を確認します。
これらはNVIDIA実機の音声生成テストの代わりにはなりません。既存A6000の更新時は既知の短文を従来ランチャーでも確認してください。

## 事前測定で分かったこと

Radeon 8060Sで、4.60秒／5.88秒の音声復元は2回目以降もCPUが約2.8〜3.0倍速かったため、復元はCPUに固定しています。
事前のGPU生成＋CPU復元では音声生成プロセスの常駐メモリ約4.6〜4.8GiB、Windows空き約5.2〜6.1GiBでした。
これらは特定条件での過去測定であり、長文・31Bカスタムの任意の量子化やコンテキスト長での保証値ではありません。
本体APIを通した今回の結果は [CX_VALIDATION.md](CX_VALIDATION.md) を参照してください。
