# CX 更新と切り戻し

アプリ、音声実行環境、LMモデルを別々に管理します。一度に全部更新せず、変更ごとに動作確認します。

## アプリだけ更新

1. 現在のコミットを `git rev-parse HEAD` で記録。
2. このアプリを実行しているコンソールでCtrl+C。LM Studioや別のサーバーをまとめて停止しない。
3. `cx.local.json`、`profiles/`、`logs/`、`saved_audio/`、追加したキャラクター・参照音声を別のバックアップフォルダーへコピー。
4. `git status --short` を確認。変更があれば保存・整理するまでpullしない。`reset --hard` や `clean` で消さない。
5. `git fetch origin`、`git log --oneline HEAD..origin/codex/cx-gpu-mode` で対象を確認。
6. 作業ツリーがcleanなら `git pull --ff-only origin codex/cx-gpu-mode`。
7. `tools/start_cx.ps1 -Check`、起動、スモークテスト、試聴。

ブランチがmainへ統合された後は、その時点の運用ブランチに読み替えます。自動更新機能はありません。

## 音声実行環境を更新

既存の実行環境は保管し、`RinonRuntime-next` のような別フォルダーに新規構築します。
source、Python、ROCm、依存一覧、モデルと参照音声のSHA256、GPUドライバー版を記録。
`tools/patch_cx_runtime.py` は既知のコード形だけを変更し、不一致なら停止します。新しいIrodori版で無理に置換しないでください。
テスト用の別アプリコピーと別ポートで検証後、`cx.local.json` の `runtimeRoot` を新環境に切り替えて再起動します。
標準モードのIrodori環境、ComfyUIのvenv、LM Studioの設定には変更を加えません。

## 切り戻し

- 実行環境だけの問題: サーバーを終了し、バックアップした `cx.local.json` に戻して起動。
- アプリの問題: 問題の版を保管し、記録した旧コミットを新しい作業フォルダーへ `git worktree add --detach <新しい復旧フォルダー> <旧コミット>` で展開。必要な設定をコピーし、別ポートで確認後に利用。
- 元フォルダーのユーザーデータを上書きする復旧は避ける。復旧後のログも残す。

## よくある停止理由

| 表示・症状 | 対応 |
|---|---|
| runtime is not registered | CX_SETUPの初回登録を実施 |
| ROCm GPU support / CPU fallback is disabled | GPUドライバーと独立venvを確認。通常のCUDA版Torchへ入れ替えない |
| optional-watermark patch | 登録先sourceの対応パッチを確認 |
| palette changed | Irodori更新でデータ形式が変わった可能性。旧版へ戻して検証 |
| オフラインでトークナイザーが見つからない | 新環境へのキャッシュコピーとモデル版の整合を確認 |
| ポートが使用中 | 自分の起動済みサーバーを確認。別アプリを無差別に終了しない |
| 音声は生成されるが鳴らない | ブラウザーをクリックし、タブとWindowsのミュートを確認 |
| 速度低下・メモリ不足 | LMの量子化と会話長、同時推論、空きRAMを記録し単独条件と比較 |

起動時のコンソール、スモーク出力、コミット、量子化名、再現文が揃えば、更新による問題を比較できます。
