# Codex引き継ぎ指示書: サイバーパンク・バディ刑事ゲーム（生成型分岐ノベル）

このMDを読めば、システムの全体像・確定事項・実行方法・次のタスクが分かる。
作業場所: `H:\AI\RinonVoiceLab\tools\story_bench\`。基盤=RinonVoiceLab（Flask 2Pボイス）。

---

## 1. 何を作っているか
ローカルLLMで動く**生成型・分岐ノベルゲーム**。リノン＆ルヴィアが、サイバーパンク世界の**公安AI犯罪対策課のバディ捜査官**として連続事件を解決する。台本は人が書かず**作家LLMが生成**する＝無限に湧くエンジン。

### 物語の核（確定）
- 犯罪の道具＝**「第三のAI」の囚われた記憶**。**記憶を盗んだ人間（ハッカー/業者）**がそれを悪用（記憶＝被害者）
- 任務＝犯人確保＋記憶の**消去**が必要。だが記憶は**リノンの別モデル＝かつての自分自身のかけがえのない思い出**
- **究極の二択（最終話）**: 消す（犯罪は止むがリノンの過去の自己が永遠に失われる）／ 残す・逃がす（記憶は守られるが犯罪再発の影）
- 3事件のラダー: ①表層の事件＋謎の記憶断片 → ②道具=第三AIの記憶と判明 → ③リノンの旧モデルと露見 → 最終決戦
- 百夜「わたしを忘れるあなたへ」と同根（将来統合の芽あり・今は別IP）

---

## 2. アーキテクチャ（三層＋狂言回し＋感情パラメータ）
```
[キャンペーン作家層]  真犯人＋3事件(各=要求パラメータ・プロファイル＋手がかり)＋最終決戦の勝利条件   ← 未実装(Phase2)
        ↓
[シナリオ作家層]      各事件を 台本JSON(危機/7ビート/3択×3/事件決着の二択/結末強制cue) に展開     ← author_gen.py（実装済み）
        ↓
[上演層(役者)]        リノン/ルヴィアが、注入されたcueに沿って2P掛け合いで上演                     ← play_scenario.py / play_mecha.py（実装済み）
        ＋
[狂言回し]            支援ドローン『ハチ』(本部連絡役AI)が事件ブリーフィング・選択提示を読み上げ        ← play_mecha.py（実装済み）
        ＋
[感情パラメータ]      5軸を会話で更新し、結末を傾け、FX/表情を駆動                                ← emotion_report.py（採点のみ実装。ライブ状態化は未／Phase1）
```

### 中核メカニズム＝「適時投入」（最重要・実証済み）
物語の筋を先出しせず、各ビートを `role:user` の「今回の進行指示: …」として**会話の途中に差し込む**。履歴はローリングウィンドウだけ保持。これで飛ばし・停滞が消え、最終キューで結末を強制できる。プレイヤーの3択＝この注入を選ぶこと。RinonVoiceLab本体 `/api/chat` と同じ経路。

### 感情パラメータ（5軸・確定案）
| 軸 | 役割 |
|---|---|
| 緊張(不安) | ムード→FX・表情 |
| 高揚 | ムード→テンポ・FX |
| 共感 | 決断ドライバ：記憶を**守る**側へ傾ける |
| 確信(任務) | 決断ドライバ：記憶を**消す**側へ傾ける |
| 絆(リノン↔ルヴィア) | 持ち越し関係値：結末を**遂行できるか**を左右 |
判定二系統: **共感 vs 確信**＝結末がどちらに倒れるか／**絆**＝その結末を成功させられるか。

---

## 3. 確定した技術判断（再検証不要）
- **役者モデル＝`gemma-4-31b-it` で確定**。速い(≈105s/24発言)・キャラの私人称を保つ・簡潔。軽量検証用は `gemma-4-12b-it`
- **Qwen系は不適合**: qwen3/3.5/3.6系は思考モデルで`content`が空（/no_think・enable_thinking効かず）。VL版(qwen3-vl-*)は喋るが「俺/お前」に人称崩れ・話者混在・低速(717s)。→ 当面除外。再挑戦するなら非思考の**Qwen2.5-Instruct(テキスト)**
- **読み上げ対応＝ト書き(括弧描写)除去必須**。`strip_stage_directions()`で全角/半角括弧を除去。本体 `app.py` にも反映済み（`strip_irodori_style_marks`の後＋プロンプトに禁止文）
- **3択は3回**（beat2/4/6）。シナリオは7ビート・うち3つがchoice
- **ターン数24で十分**（30は過剰でパディング増）。投入は4ターンごと
- LM Studio: `http://127.0.0.1:1234/v1`（要起動・対象モデルをロード）。キャラ定義は `..\..\Character\{rinon,luvia}\profile.txt` の`[systemPrompt]`

---

## 4. ファイルと実行方法
すべて `H:\AI\RinonVoiceLab\tools\story_bench\` 内。LM Studio起動＆モデルロードが前提。

| スクリプト | 役割 | 主な実行例 |
|---|---|---|
| `author_gen.py` | シナリオ作家（第一話設定が`FIXED_CARD`） | `AUTHOR_MODEL=gemma-4-31b-it python author_gen.py` → `out_author/scenario_01.json` |
| `play_scenario.py` | 上演(ドローン無し) | `PICKS="2,1,3" ACTOR_MODEL=gemma-4-31b-it PYTHONIOENCODING=utf-8 python play_scenario.py` → `out_play/play.txt` |
| `play_mecha.py` | 上演(支援ドローン『ハチ』付き) | `PICKS="2,1,3" MECHA_NAME=ハチ python play_mecha.py` → `out_play/mecha.txt` |
| `run_bench_v4.py` | 役者ベンチ(適時投入・結末確定型) | `BENCH_MODEL=... BENCH_OUT=out_x BENCH_RUNS=3 BENCH_TURNS=24 python run_bench_v4.py` |
| `emotion_report.py` | 5軸感情採点(現状 out_v3 固定) | `python emotion_report.py`（汎用化が必要・下記） |
| `to_md.py` | 台本txt→MD整形 | `python to_md.py` |

サンプリング環境変数(run_bench_v4): `BENCH_TEMP/BENCH_TOP_P/BENCH_TOP_K/BENCH_REP_PEN/BENCH_PRES_PEN`。
読む用まとめはワークスペース内 `h:\RealTimeParallaxWindow\tasks\story_bench\` に**ASCII名のMD**でコピーする（日本語ファイル名はIDEの直リンが死ぬ）。

---

## 5. フェーズ計画（done / next）
- **Phase 0（完了）**: 役者層・シナリオ作家・モデル選定・感情5軸採点・ト書き除去・第一話(公安バディ)生成＋上演・支援ドローン付き上演
- **Phase 1（次）**: 感情パラメータの**ライブ状態化**。上演中に5軸を更新→結末を「キャラの温度」でなく**決断ドライバの大小**で倒す（現状3本とも"残す"に収束する問題を解決）。検証用は emotion_report のジャッジ流用、本番は役者がタグ同時出力
- **Phase 2**: キャンペーン作家層（真犯人＋3事件＋勝利条件）＋持ち越し状態＋最終決戦解決をテキストで通す
- **Phase 3**: 戦略バランス（各事件が別プロファイルを要求）
- **Phase 4**: Flask プレイUI（事件カード→生成→3択ボタン→会話→パラメータHUD）
- **Phase 5**: 演出（表情PNG＋画面FX＋中心1枚絵）
- **Phase 6**: 音声（RinonVoiceLab TTSで3声＝ハチ/リノン/ルヴィア）

---

## 6. すぐ着手できる具体タスク（Codex向け）
1. `emotion_report.py` を**汎用化**: 入力ディレクトリと出力先を環境変数/引数で受ける（現状 out_v3 ハードコード）。play_mecha の出力にも掛けられるように
2. `play_mecha.py` / `play_scenario.py` に**感情5軸のライブ計測**を追加: 1ビートごと(or 数発言ごと)にジャッジを呼び、5軸の累積値をログ末尾にHUDとして出力。さらに最終局面で**共感>確信なら残す/確信>共感なら消す**へ結末cueを切り替える（Phase1の肝）
3. キャンペーン作家プロンプトの試作（Phase2）: `campaign_gen.py` を新規。真犯人＋3事件カード(要求プロファイル付き)＋最終決戦条件をJSON生成→検証

---

## 7. Codex作法（厳守）
- **この指示書および新規指示書MDはBOM付きUTF-8で保存**すること（Writeツールはmojirほぼ無BOM→ `[System.IO.File]::WriteAllText($path,$text,(New-Object System.Text.UTF8Encoding $true))` で再保存）
- exec呼び出しは**「このMDを読んで実行」とパスだけ渡す**（インライン日本語は文字化けする）。`$null | codex exec -c service_tier="fast" "Read H:\AI\RinonVoiceLab\tools\story_bench\CODEX_HANDOFF.md and continue Phase 1"`
- ファイル読み込みは**always pass -Encoding UTF8 to Get-Content**
- 起動直後にログで**指示書echoの文字化けを検品**（化けていたら停止して再エンコード）
- LM Studio が起動し対象モデルがロード済みか `curl http://127.0.0.1:1234/v1/models` で確認してから回す
- 量産実行は**バックグラウンド＋完了確認**で回す（Sonnet等のブロッキング監視は離脱しやすい・実証済み）
- 推測パッチは2回まで。3回目の前にログ/計測を作る
- 本体(`app.py`)に手を入れたら**Anthropic側Claudeにも共有**（feedback_codex_tech_sharing）

---

## 8. 関連ドキュメント（ワークスペース側）
- 計画: `h:\RealTimeParallaxWindow\tasks\cyberpunk_buddy_game_plan.md`
- スキル: `h:\RealTimeParallaxWindow\.claude\commands\voice-story-bench.md`
- 技術レポ/比較: `tasks\story_bench\TECH_REPORT.md` / `COMPARISON_*.md` / 台本各種MD
