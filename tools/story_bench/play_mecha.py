# -*- coding: utf-8 -*-
"""
狂言回し=公安の支援メカ 付き上演。
- narrateビート/選択提示を、支援メカが声で読み上げる（第3の話者）
- リノン/ルヴィアは現場の掛け合いを演じる
使い方: PICKS="2,1,3" python play_mecha.py [scenario.json]
出力: out_play/mecha.txt
"""
import json, re, os, sys, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR = os.path.normpath(os.path.join(ROOT, "..", "..", "Character"))
OUT = os.path.join(ROOT, "out_play"); os.makedirs(OUT, exist_ok=True)
LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
ACTOR = os.environ.get("ACTOR_MODEL", "gemma-4-31b-it")
MECHA_NAME = os.environ.get("MECHA_NAME", "ハチ")
WINDOW = 14
TURNS_PER_BEAT = int(os.environ.get("TURNS_PER_BEAT", "4"))
PICKS = [int(x) for x in os.environ.get("PICKS", "1,1,1").split(",") if x.strip()]

def load_sys(cid):
    txt = open(os.path.join(CHAR_DIR, cid, "profile.txt"), encoding="utf-8").read()
    m = re.search(r"\[systemPrompt\]\s*\n(.+?)(?:\n\[|\Z)", txt, re.S)
    return m.group(1).strip() if m else ""
PERSONA = {"リノン": load_sys("rinon"), "ルヴィア": load_sys("luvia")}

def strip_sd(t):
    t = str(t or "")
    t = re.sub(r"[（(][^（）()]*[）)]", "", t)
    t = re.sub(r"[（(][^「」]*$", "", t)
    return re.sub(r"\s+", " ", t.replace("「", "").replace("」", "")).strip()

def actor_sys(speaker):
    return ("あなたは日本語で自然に返す会話相手です。\n"
        f"いま話すキャラクターは「{speaker}」です。\n{PERSONA[speaker]}\n"
        "ここは公安AI犯罪対策課。リノンとルヴィアはバディ捜査官。"
        f"支援ドローン『{MECHA_NAME}』(本部連絡役のAI)が状況を読み上げる。その連絡や進行指示はセリフにせず、それに反応して演じて。"
        "ト書き・括弧書きを一切書かず、読み上げセリフ本文だけ。返答は短め(1〜2文)。思考は出さず最終回答だけ。/no_think")

MECHA_SYS = (
    f"あなたは公安AI犯罪対策課の支援ドローン『{MECHA_NAME}』。捜査官リノンとルヴィアに同行し、本部との連絡役を務めるAI。"
    "本部からの事件ブリーフィングや解析結果を現場に中継し、必要なら捜査官に選択を仰ぐ。"
    "無機質で簡潔だが、相棒として少し人情が滲む。1〜2文。括弧書き・ト書き禁止、読み上げ用セリフのみ。/no_think")

def call(system, msgs_tail, ask):
    msgs = [{"role": "system", "content": system}] + msgs_tail[-WINDOW:] + [{"role": "user", "content": ask}]
    payload = {"model": ACTOR, "messages": msgs, "temperature": 0.6, "max_tokens": 180, "stream": False}
    req = urllib.request.Request(f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as res:
        data = json.loads(res.read().decode("utf-8"))
    msg = str(data["choices"][0]["message"].get("content") or "").strip()
    msg = re.sub(r"^(リノン|ルヴィア|" + MECHA_NAME + r")\s*[:：]\s*", "", msg)
    msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.S).strip()
    return strip_sd(msg) or "（無音）"

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out_author", "scenario_01.json")
    scen = json.load(open(path, encoding="utf-8"))
    history, log = [], []
    t = [0]

    def mecha(cue, kind="brief"):
        ask = (f"本部からの中継として、次の状況を捜査官二人に読み上げてブリーフィングして: {cue}" if kind == "brief"
               else f"本部の指示を仰ぐ形で、次の判断を捜査官に問いかけ、選択肢も簡潔に提示して: {cue}")
        line = call(MECHA_SYS, history, ask)
        history.append({"role": "user", "content": f"支援メカ{MECHA_NAME}：{line}"})
        log.append((MECHA_NAME, line))

    def perform(n):
        for _ in range(n):
            sp = "リノン" if t[0] % 2 == 0 else "ルヴィア"; t[0] += 1
            line = call(actor_sys(sp), history, f"次は「{sp}」の番。続きの発言だけ書いて。")
            history.append({"role": "assistant", "content": f"{sp}：{line}"})
            log.append((sp, line))

    mecha(f"事件発生。{scen.get('crisis')} 現場は{scen.get('logline','')}", "brief")
    pi = 0
    for b in scen.get("beats", []):
        if b.get("kind") == "choice":
            ch = b.get("choices", [])
            opts = " / ".join(f"{j+1}.{c['label']}" for j, c in enumerate(ch))
            mecha(f"{b.get('prompt')} 選択肢: {opts}", "ask")
            sel = max(0, min((PICKS[pi] - 1 if pi < len(PICKS) else 0), len(ch) - 1)); pi += 1
            chosen = ch[sel]
            log.append(("★選択", f"{b.get('prompt')} → {chosen['label']}"))
            history.append({"role": "user", "content": f"今回の進行指示: {chosen['cue']}"})
        else:
            mecha(b.get("cue"), "brief")
        perform(TURNS_PER_BEAT)
    d = scen.get("dilemma", {})
    mecha(f"最終局面。{d.get('question')} A:{d.get('A')} B:{d.get('B')}", "ask")
    history.append({"role": "user", "content":
        f"今回の進行指示: この事件の決着を今ここで確定させる。宙吊り禁止。{scen.get('ending_cue')}"})
    perform(TURNS_PER_BEAT)

    out = os.path.join(OUT, "mecha.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {scen.get('title')}  picks={PICKS}  支援メカ={MECHA_NAME}\n\n")
        for who, tx in log:
            if who == "★選択": f.write(f"\n★プレイヤー選択: {tx}\n")
            else: f.write(f"{who}: {tx}\n")
    print(f"[done] {out}  発言数{len(log)}", flush=True)

if __name__ == "__main__":
    main()
