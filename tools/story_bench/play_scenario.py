# -*- coding: utf-8 -*-
"""
縦の一本: 作家LLMが生成したシナリオJSONを役者層(リノン/ルヴィア2P)で上演する。
- narrateビート=進行指示を注入 / choiceビート=プレイヤーが選んだ選択肢のcueを注入
- 最後にdilemma+ending_cueを注入して結末を必ず確定
- ト書き除去込み（読み上げ可能なセリフのみ）
使い方: PICKS="2,1" (choiceビートの選択肢番号を順に) python play_scenario.py [scenario.json]
出力: out_play/play.txt
"""
import json, re, os, sys, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR = os.path.normpath(os.path.join(ROOT, "..", "..", "Character"))
OUT = os.path.join(ROOT, "out_play"); os.makedirs(OUT, exist_ok=True)
LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
ACTOR = os.environ.get("ACTOR_MODEL", "gemma-4-31b-it")
WINDOW = 12
TURNS_PER_BEAT = int(os.environ.get("TURNS_PER_BEAT", "4"))
PICKS = [int(x) for x in os.environ.get("PICKS", "1,1").split(",") if x.strip()]

def load_sys(cid):
    txt = open(os.path.join(CHAR_DIR, cid, "profile.txt"), encoding="utf-8").read()
    m = re.search(r"\[systemPrompt\]\s*\n(.+?)(?:\n\[|\Z)", txt, re.S)
    return m.group(1).strip() if m else ""
PERSONA = {"リノン": load_sys("rinon"), "ルヴィア": load_sys("luvia")}

def strip_stage_directions(t):
    t = str(t or "")
    t = re.sub(r"[（(][^（）()]*[）)]", "", t)
    t = re.sub(r"[（(][^「」]*$", "", t)
    return re.sub(r"\s+", " ", t.replace("「", "").replace("」", "")).strip()

def system_msg(speaker):
    return ("あなたは日本語で自然に返す会話相手です。\n"
        f"いま話すキャラクターは「{speaker}」です。\n{PERSONA[speaker]}\n"
        "2人だけモードです。観客やユーザーはいません。リノンとルヴィアだけが互いに話します。"
        "「今回の進行指示」はナレーターの舞台指示。それ自体をセリフにせず、指示に沿って次の展開を演じて。"
        "ト書き・状況説明・括弧書きを一切書かず、読み上げられるセリフ本文だけを出すこと。"
        "返答は短め(1〜3文)。思考過程は出さず最終回答だけ。/no_think")

def call(speaker, history):
    msgs = [{"role": "system", "content": system_msg(speaker)}] + history[-WINDOW:]
    msgs.append({"role": "user", "content": f"次は「{speaker}」の番です。続きの発言だけを書いてください。"})
    payload = {"model": ACTOR, "messages": msgs, "temperature": 0.7, "max_tokens": 220, "stream": False}
    req = urllib.request.Request(f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as res:
        data = json.loads(res.read().decode("utf-8"))
    msg = str(data["choices"][0]["message"].get("content") or "").strip()
    msg = re.sub(r"^(リノン|ルヴィア)\s*[:：]\s*", "", msg)
    msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.S).strip()
    return strip_stage_directions(msg) or "（無音）"

def inject(history, log, text):
    history.append({"role": "user", "content": f"今回の進行指示: {text}"})
    log.append(("DIRECTOR", text))

def perform(history, log, n, t0=[0]):
    for _ in range(n):
        speaker = "リノン" if t0[0] % 2 == 0 else "ルヴィア"
        t0[0] += 1
        line = call(speaker, history)
        history.append({"role": "assistant", "content": f"{speaker}：{line}"})
        log.append((speaker, line))

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out_author", "scenario_01.json")
    scen = json.load(open(path, encoding="utf-8"))
    print(f"[play] actor={ACTOR}  picks={PICKS}  title={scen.get('title')}", flush=True)
    print(f"危機: {scen.get('crisis')}", flush=True)
    history, log = [], []
    inject(history, log, f"舞台設定: {scen.get('crisis')} この危機の中で物語が進む。")
    pi = 0
    for b in scen.get("beats", []):
        if b.get("kind") == "choice":
            ch = b.get("choices", [])
            sel = PICKS[pi] - 1 if pi < len(PICKS) else 0
            pi += 1
            sel = max(0, min(sel, len(ch) - 1))
            chosen = ch[sel]
            print(f"  [選択 beat{b['id']}] {b.get('prompt')} → 「{chosen.get('label')}」", flush=True)
            log.append(("CHOICE", f"{b.get('prompt')} → {chosen.get('label')}"))
            inject(history, log, chosen.get("cue"))
        else:
            inject(history, log, b.get("cue"))
        perform(history, log, TURNS_PER_BEAT)
    # 結末確定
    d = scen.get("dilemma", {})
    final = (f"究極の二択を今ここで決着させる。宙吊り禁止。{d.get('question')} "
             f"A={d.get('A')} / B={d.get('B')} のどちらかに二人の判断で確定し、{scen.get('ending_cue')}")
    inject(history, log, final)
    perform(history, log, TURNS_PER_BEAT)
    # 出力
    out = os.path.join(OUT, "play.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {scen.get('title')}  picks={PICKS}\n# 危機: {scen.get('crisis')}\n\n")
        for who, tx in log:
            if who == "DIRECTOR": f.write(f"\n〈進行指示〉{tx}\n")
            elif who == "CHOICE": f.write(f"\n★プレイヤー選択: {tx}\n")
            else: f.write(f"{who}: {tx}\n")
    print(f"\n--- 最終5発言 ---", flush=True)
    for who, tx in [x for x in log if x[0] in ("リノン", "ルヴィア")][-5:]:
        print(f"{who}: {tx}", flush=True)
    print(f"\n[done] {out}", flush=True)

if __name__ == "__main__":
    main()
