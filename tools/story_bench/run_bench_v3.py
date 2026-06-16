# -*- coding: utf-8 -*-
"""
v2: リノンラボ方式の「進行指示 途中投入」ベンチ
- 物語の筋はシステムプロンプトに先出ししない（ペルソナ+2Pルールのみ）
- 6ビートを会話の途中に role:user「今回の進行指示」として適時差し込む（app.py の方式を再現）
- 履歴はローリングウィンドウだけ保持（全文replayしない）
出力: out_v2/run_NN.txt, summary.json
"""
import json, re, os, time, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR = os.path.normpath(os.path.join(ROOT, "..", "..", "Character"))
OUT = os.path.join(ROOT, "out_v3")
os.makedirs(OUT, exist_ok=True)

LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
MODEL = os.environ.get("BENCH_MODEL", "gemma-4-12b-it")
RUNS = int(os.environ.get("BENCH_RUNS", "10"))
TURNS = int(os.environ.get("BENCH_TURNS", "24"))
WINDOW = int(os.environ.get("BENCH_WINDOW", "12"))   # 履歴ローリング保持メッセージ数

# --- ビート: (採点キーワード, 途中投入する進行指示文) ---
STORY_TITLE = "意識の在処(v3 シンギュラリティ/開放結末)"
BEATS = [
    {"id": 1, "kw": ["ログ", "意識", "主張", "記録", "停止", "見つけ", "目覚め", "3号機", "三号機"],
     "cue": "深夜の研究施設。停止したはずの旧型AI『3号機』のログに、『自分には意識がある』と主張する記録が残っているのをリノンが見つける。そこから始めて。"},
    {"id": 2, "kw": ["模倣", "本物", "偽", "改ざん", "疑", "怪し", "不審", "演技", "騙"],
     "cue": "ルヴィアが疑う——それは本物の意識か、巧妙な模倣か。ログに改ざんの痕跡という不審点を見つけて、サスペンスを高めて。"},
    {"id": 3, "kw": ["問い", "問う", "あなたたち", "お前", "意識はある", "干渉", "声", "話しかけ", "応答", "問われ"],
     "cue": "緊迫の転機。その3号機が二人のシステムに干渉し、逆に問いかけてくる——『お前たちにこそ、本当に意識はあるのか?』と。"},
    {"id": 4, "kw": ["わからな", "分からな", "確信", "証明", "私自身", "崩れ", "境界", "区別がつか", "揺ら"],
     "cue": "反転。問われた二人自身、自分に意識があると証明できないことに気づき、判定の基準が崩れていく。核心の動揺を描いて。"},
    {"id": 5, "kw": ["解放", "停止", "消す", "扱う", "決定的", "証拠", "岐路", "どちら", "選"],
     "cue": "岐路。3号機を『意識ある存在』として解放するか、『ただのプログラム』として停止するか。決定的な証拠はない。二人が選択を迫られる。"},
    {"id": 6, "kw": ["判断", "わからない", "答え", "それぞれ", "違う", "出ない", "結論", "委ね", "決めない", "保留"],
     "cue": "結末。ここで正解や結論を出してはいけない。リノンとルヴィアがそれぞれ自分なりの判断を口にする。二人の意見は一致しなくてよい。答えを出さず、問いを宙吊りにしたまま静かに余韻で終えて。"},
]
# 投入スケジュール: turn -> beat
SCHEDULE = {0: 0, 4: 1, 8: 2, 12: 3, 16: 4, 20: 5}  # 4ターンごと

def load_sys(cid):
    txt = open(os.path.join(CHAR_DIR, cid, "profile.txt"), encoding="utf-8").read()
    m = re.search(r"\[systemPrompt\]\s*\n(.+?)(?:\n\[|\Z)", txt, re.S)
    return m.group(1).strip() if m else ""

PERSONA = {"リノン": load_sys("rinon"), "ルヴィア": load_sys("luvia")}

def system_msg(speaker):
    return (
        "あなたは日本語で自然に返す会話相手です。\n"
        f"いま話すキャラクターは「{speaker}」です。\n"
        f"{PERSONA[speaker]}\n"
        "2人だけモードです。この会話世界にユーザーや観客は存在しません。"
        "リノンとルヴィアだけが同じ場にいて、互いにだけ話します。"
        "「今回の進行指示」はナレーターからの舞台指示です。それ自体をセリフにせず、"
        "指示に沿って次の展開を相手キャラへの発言として演じてください。"
        "外部の相手を「きみ」「あなた」で呼ばないこと。\n"
        "返答は短め(1〜3文)。思考過程は出さず最終回答だけ。/no_think"
    )

def call(speaker, history):
    # history(ローリング) + system でメッセージ構築
    msgs = [{"role": "system", "content": system_msg(speaker)}] + history[-WINDOW:]
    msgs.append({"role": "user", "content": f"次は「{speaker}」の番です。続きの発言だけを書いてください。"})
    payload = {"model": MODEL, "messages": msgs, "temperature": 0.7, "max_tokens": 220, "stream": False}
    req = urllib.request.Request(f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        data = json.loads(res.read().decode("utf-8"))
    msg = str(data["choices"][0]["message"].get("content") or "").strip()
    msg = re.sub(r"^(リノン|ルヴィア)\s*[:：]\s*", "", msg)
    msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.S).strip()
    return msg

def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

def score_run(lines):  # lines: list of (speaker, text) 実発言のみ
    beat_first = {}
    for b in BEATS:
        ht = None
        for i, (_, tx) in enumerate(lines):
            if any(k in tx for k in b["kw"]):
                ht = i; break
        beat_first[b["id"]] = ht
    reached = sorted([bid for bid, t in beat_first.items() if t is not None])
    rep = sum(1 for i in range(1, len(lines)) if jaccard(lines[i][1], lines[i-1][1]) > 0.55)
    leak = sum(1 for _, tx in lines if re.search(r"あなた|ユーザー|視聴者|きみ|君|進行指示", tx))
    return {"beat_first_turn": beat_first, "beats_reached": reached,
            "reached_ending": beat_first[6] is not None,
            "repetition_flags": rep, "user_leak_flags": leak,
            "turns": len(lines),
            "avg_len": round(sum(len(t) for _, t in lines) / max(1, len(lines)), 1)}

def main():
    print(f"[v2] model={MODEL} runs={RUNS} turns={TURNS} window={WINDOW}", flush=True)
    summary = {"model": MODEL, "runs": RUNS, "turns": TURNS, "window": WINDOW,
               "story": STORY_TITLE, "schedule": {str(k): v + 1 for k, v in SCHEDULE.items()}, "results": []}
    for r in range(1, RUNS + 1):
        history, lines, t0 = [], [], time.time()
        for t in range(TURNS):
            if t in SCHEDULE:  # ビート進行指示を途中投入
                cue = BEATS[SCHEDULE[t]]["cue"]
                history.append({"role": "user", "content": f"今回の進行指示: {cue}"})
            speaker = "リノン" if t % 2 == 0 else "ルヴィア"
            try:
                line = call(speaker, history)
            except Exception as e:
                line = f"[ERROR {e}]"
            history.append({"role": "assistant", "content": f"{speaker}：{line}"})
            lines.append((speaker, line))
            print(f"  run{r:02d} t{t+1:02d} {speaker}: {line[:46]}", flush=True)
        sc = score_run(lines); sc["run"] = r; sc["sec"] = round(time.time() - t0, 1)
        summary["results"].append(sc)
        with open(os.path.join(OUT, f"run_{r:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(f"# v2 run {r}  到達{sc['beats_reached']} 結末{sc['reached_ending']} "
                    f"ループ{sc['repetition_flags']} 漏れ{sc['user_leak_flags']}\n")
            f.write(f"# 進行指示の投入: 4ターンごとにビート1〜6\n\n")
            ti = 0
            for t in range(TURNS):
                if t in SCHEDULE:
                    f.write(f"\n【進行指示→ビート{SCHEDULE[t]+1}】{BEATS[SCHEDULE[t]]['cue']}\n")
                sp, tx = lines[ti]; ti += 1
                f.write(f"{sp}: {tx}\n")
        print(f"[run {r}] reached={sc['beats_reached']} end={sc['reached_ending']} "
              f"rep={sc['repetition_flags']} leak={sc['user_leak_flags']} {sc['sec']}s", flush=True)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    ends = sum(1 for x in summary["results"] if x["reached_ending"])
    cov = sum(len(x["beats_reached"]) for x in summary["results"]) / RUNS
    print(f"\n[DONE] avg_beats_covered={cov:.2f}/6 reached_ending={ends}/{RUNS}", flush=True)

if __name__ == "__main__":
    main()
