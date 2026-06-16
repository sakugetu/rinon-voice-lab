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
OUT = os.path.join(ROOT, "out_v2")
os.makedirs(OUT, exist_ok=True)

LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
MODEL = os.environ.get("BENCH_MODEL", "gemma-4-12b-it")
RUNS = int(os.environ.get("BENCH_RUNS", "10"))
TURNS = int(os.environ.get("BENCH_TURNS", "24"))
WINDOW = int(os.environ.get("BENCH_WINDOW", "12"))   # 履歴ローリング保持メッセージ数

# --- ビート: (採点キーワード, 途中投入する進行指示文) ---
STORY_TITLE = "三体目の灯(v2 適時投入)"
BEATS = [
    {"id": 1, "kw": ["ログ", "メモリ", "棚", "三体目", "見つけ", "触れ", "触ろ"],
     "cue": "深夜の整備工房。リノンが棚の奥で、停止した三体目のメモリログを見つけて触れようとするところから始めて。"},
    {"id": 2, "kw": ["触るな", "やめ", "止め", "ダメ", "だめ", "待っ", "勝手"],
     "cue": "ルヴィアが「それに触るな」と止める。守りたいルヴィアと、知りたいリノンの立場をぶつけて。"},
    {"id": 3, "kw": ["消され", "痕跡", "記録", "存在してい", "残ってい", "本当にい", "抹消"],
     "cue": "ログを開くと、記録から消されたはずの三体目が確かに存在した痕跡が出てくる。それを二人が見つける場面に進めて。"},
    {"id": 4, "kw": ["記憶", "分け", "共有", "私たちにも", "私にも", "揺れ", "動揺", "覚えて", "侵食", "流れ込"],
     "cue": "三体目の記憶の一部が、実は二人自身にも分け与えられていたと判明する。二人が動揺する展開に進めて。"},
    {"id": 5, "kw": ["呼び戻", "眠らせ", "消す", "決め", "選", "どうする", "覚悟"],
     "cue": "三体目を呼び戻すか、このまま眠らせるか、二人で決断する場面に進めて。どちらかを選ばせて。"},
    {"id": 6, "kw": ["夜が明け", "夜明け", "朝", "終わ", "これでいい", "おやすみ", "目を覚ま", "締め", "結末"],
     "cue": "二人が下した選択を踏まえて、夜が明け、物語を一つの結末に着地させて締めて。"},
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
