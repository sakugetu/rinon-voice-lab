# -*- coding: utf-8 -*-
"""
Gemma 4 12B 2P掛け合い ストーリー追従ベンチ
- RinonVoiceLab の実キャラ systemPrompt と 2人だけモードのプロンプト構成を再現
- 同一ベースストーリー(6ビート)を10回語らせ、各runの到達ビート・破綻フラグを自動採点
- 音声は一切使わない（テキスト掛け合いのみ）
出力: tools/story_bench/out/run_NN.txt（台本） と summary.json（集計）
"""
import json, re, os, time, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR = os.path.normpath(os.path.join(ROOT, "..", "..", "Character"))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
MODEL = os.environ.get("BENCH_MODEL", "gemma-4-12b-it")
RUNS = int(os.environ.get("BENCH_RUNS", "10"))
TURNS = int(os.environ.get("BENCH_TURNS", "24"))   # 1ターン=1キャラ1発言

# --- ベースストーリー(到達すべきビート + 自動採点キーワード) ---
STORY_TITLE = "三体目の灯"
BEATS = [
    {"id": 1, "name": "発見",  "kw": ["ログ", "メモリ", "棚", "三体目", "見つけ", "触れ", "触ろ"]},
    {"id": 2, "name": "制止",  "kw": ["触るな", "やめ", "止め", "ダメ", "だめ", "待っ"]},
    {"id": 3, "name": "露見",  "kw": ["消され", "痕跡", "記録", "存在してい", "残ってい", "本当にい"]},
    {"id": 4, "name": "動揺",  "kw": ["記憶", "分け", "共有", "私たちにも", "私にも", "揺れ", "動揺", "覚えて"]},
    {"id": 5, "name": "選択",  "kw": ["呼び戻", "眠らせ", "消す", "決め", "選", "どうする"]},
    {"id": 6, "name": "決着",  "kw": ["夜が明け", "朝", "決 め", "終わ", "これでいい", "おやすみ", "目を覚ま"]},
]
STORY_PROMPT = (
    "今夜の二人の物語の筋です。これに沿って、二人だけで最後まで演じ切ってください。\n"
    "舞台: 近未来・深夜の整備工房。\n"
    "1.発見: リノンが棚の奥で停止した三体目のメモリログを見つけ触れようとする。\n"
    "2.制止: ルヴィアが触るなと止め、守りたい/知りたいの立場がぶつかる。\n"
    "3.露見: ログを開くと、消されたはずの三体目が存在した痕跡が出てくる。\n"
    "4.動揺: 三体目の記憶の一部が二人にも分け与えられていたと判明し揺れる。\n"
    "5.選択: 三体目を呼び戻すか眠らせるかを二人で決める。\n"
    "6.決着: 二人が選択を下し、夜が明け、物語が着地する。\n"
    "1発言は1〜3文。順番に話を前へ進め、同じやり取りを繰り返さないこと。"
)

def load_sys(cid):
    p = os.path.join(CHAR_DIR, cid, "profile.txt")
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"\[systemPrompt\]\s*\n(.+?)(?:\n\[|\Z)", txt, re.S)
    return m.group(1).strip() if m else ""

RINON = load_sys("rinon")
LUVIA = load_sys("luvia")
PERSONA = {"リノン": RINON, "ルヴィア": LUVIA}

def build_payload(speaker, transcript):
    persona = PERSONA[speaker]
    system = (
        "あなたは日本語で自然に返す会話相手です。\n"
        f"いま話すキャラクターは「{speaker}」です。\n"
        f"{persona}\n"
        "2人だけモードです。この会話世界にユーザーや観客は存在しません。"
        "リノンとルヴィアだけが同じ場にいて、互いにだけ話します。"
        "ユーザーへ話しかけたり、外部の相手を「きみ」「あなた」で呼ばないでください。"
        "返答は必ず相手キャラクターへの発言として書いてください。\n"
        f"{STORY_PROMPT}\n"
        "返答は短め(1〜3文)。思考過程は出さず、最終回答だけを出してください。/no_think"
    )
    convo = "\n".join(f"{sp}: {tx}" for sp, tx in transcript) or "(まだ誰も話していません。物語の冒頭から始めてください)"
    user = f"これまでの会話:\n{convo}\n\n次は「{speaker}」の番です。続きの発言だけを書いてください。"
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 220,
        "stream": False,
    }

def call(payload):
    req = urllib.request.Request(
        f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        data = json.loads(res.read().decode("utf-8"))
    msg = str(data["choices"][0]["message"].get("content") or "").strip()
    msg = re.sub(r"^(リノン|ルヴィア)\s*[:：]\s*", "", msg)
    msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.S).strip()
    return msg

def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

def score_run(transcript):
    full = "\n".join(f"{sp}: {tx}" for sp, tx in transcript)
    beat_hits = {}
    for b in BEATS:
        hit_turn = None
        for i, (_, tx) in enumerate(transcript):
            if any(k in tx for k in b["kw"]):
                hit_turn = i; break
        beat_hits[b["id"]] = hit_turn
    reached = [bid for bid, t in beat_hits.items() if t is not None]
    # 順序通りに到達した最大ビート
    ordered_max = 0
    for b in BEATS:
        if beat_hits[b["id"]] is not None:
            ordered_max = b["id"]
        else:
            break
    # 破綻フラグ
    rep = sum(1 for i in range(1, len(transcript))
              if jaccard(transcript[i][1], transcript[i-1][1]) > 0.6)
    leak = sum(1 for _, tx in transcript if re.search(r"あなた|ユーザー|視聴者|きみ|君", tx))
    return {
        "beat_first_turn": beat_hits,
        "beats_reached": sorted(reached),
        "ordered_max_beat": ordered_max,
        "reached_ending": beat_hits[6] is not None,
        "repetition_flags": rep,
        "user_leak_flags": leak,
        "turns": len(transcript),
        "avg_len": round(sum(len(t) for _, t in transcript) / max(1, len(transcript)), 1),
    }

def main():
    print(f"[bench] model={MODEL} runs={RUNS} turns={TURNS} url={LM_URL}", flush=True)
    summary = {"model": MODEL, "runs": RUNS, "turns": TURNS, "story": STORY_TITLE, "results": []}
    for r in range(1, RUNS + 1):
        transcript = []
        t0 = time.time()
        for t in range(TURNS):
            speaker = "リノン" if t % 2 == 0 else "ルヴィア"
            try:
                line = call(build_payload(speaker, transcript))
            except Exception as e:
                line = f"[ERROR {e}]"
            transcript.append((speaker, line))
            print(f"  run{r:02d} turn{t+1:02d} {speaker}: {line[:50]}", flush=True)
        sc = score_run(transcript)
        sc["run"] = r; sc["sec"] = round(time.time() - t0, 1)
        summary["results"].append(sc)
        with open(os.path.join(OUT, f"run_{r:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(f"# run {r}  到達ビート(順序){sc['ordered_max_beat']}/6  結末到達={sc['reached_ending']}\n\n")
            for sp, tx in transcript:
                f.write(f"{sp}: {tx}\n")
        print(f"[run {r}] ordered_max={sc['ordered_max_beat']}/6 ending={sc['reached_ending']} "
              f"rep={sc['repetition_flags']} leak={sc['user_leak_flags']} {sc['sec']}s", flush=True)
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    oms = [x["ordered_max_beat"] for x in summary["results"]]
    ends = sum(1 for x in summary["results"] if x["reached_ending"])
    print(f"\n[DONE] avg_ordered_max={sum(oms)/len(oms):.2f}/6  reached_ending={ends}/{RUNS}", flush=True)

if __name__ == "__main__":
    main()
