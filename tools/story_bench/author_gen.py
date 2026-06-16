# -*- coding: utf-8 -*-
"""
作家層プロトタイプ: 状況メニュー生成 → 選択 → あらすじ(シナリオ)JSON展開
- 役者層(リノン/ルヴィアの2P掛け合い)が食える構造化データを作家LLMに吐かせる
- 出力: out_author/menu.json, scenario_NN.json
"""
import json, re, os, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out_author")
os.makedirs(OUT, exist_ok=True)
LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
AUTHOR = os.environ.get("AUTHOR_MODEL", "gemma-4-31b-it")

def chat(system, user, max_tokens=1800):
    payload = {"model": AUTHOR, "temperature": 0.8, "max_tokens": max_tokens, "stream": False,
        "messages": [{"role": "system", "content": system + " /no_think"},
                     {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=240) as res:
        txt = json.loads(res.read().decode("utf-8"))["choices"][0]["message"]["content"]
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.search(r"\{.*\}|\[.*\]", txt, re.S)
    return json.loads(m.group(0))

MENU_SYS = (
    "あなたは二人のアンドロイド少女(リノン=情で揺れる/ルヴィア=確信で突き放す)が主役の、"
    "短い対話劇のお題を作る作家です。プレイヤーが選ぶ『状況カード』を作ります。"
    "各カードは、冒頭から動いている危機を含み、最後に正解のない究極の二択へ向かう余地があること。"
    "出力はJSON配列のみ。各要素 {\"id\":n,\"title\":\"短い題\",\"logline\":\"一文の状況説明(危機を含む)\",\"hook\":\"なぜ二択に追い込まれるか\"}。"
)
SCEN_SYS = (
    "あなたはサイバーパンク刑事ドラマの構成作家です。舞台は近未来都市・公安AI犯罪対策課。"
    "リノン(情で踏み込む)とルヴィア(冷徹で任務遂行型)はバディ捜査官。"
    "これは連続事件キャンペーンの『第一の事件』。小さな事件として必ず決着させるが、"
    "結末では背後の大きな謎『第三のAIの囚われた記憶』への伏線(記憶の断片という手がかり)を残すこと。"
    "最終話の究極の二択(記憶を消す/残す)はここでは出さない。"
    "与えられた状況カードを、二人が演じる台本の設計図に展開します。必ず次のJSONだけを返す:\n"
    "{\"title\":..,\"logline\":..,\"crisis\":\"冒頭から動く時限的危機\","
    "\"beats\":[ {\"id\":1,\"kind\":\"narrate\",\"cue\":\"進行指示文(その場面へ二人を導く)\"},"
    " {\"id\":3,\"kind\":\"choice\",\"prompt\":\"プレイヤーへの問い\",\"choices\":[{\"label\":\"短い選択肢\",\"cue\":\"選ばれた時に注入する進行指示\"} を必ず3つ] } ... 全6ビート ],"
    "\"dilemma\":{\"question\":\"この事件の決着で迫られる選択(正解なし)\",\"A\":\"選択肢A\",\"B\":\"選択肢B\"},"
    "\"ending_cue\":\"この第一の事件を必ず決着させ(宙吊り厳禁)、最後に『記憶の断片』という手がかりを掴んで次の事件への引きを残す、と二人に指示する文\"}\n"
    "制約: beatsは7個。うち**ちょうど3個**をkind=choice(各choices3つ・意味的に割れること)で、"
    "物語の前半・中盤・終盤に散らすこと。残り4個はnarrate。beat1はnarrate(事件現場・状況の提示)、"
    "最後のbeatはnarrateで事件の決着局面へ追い込む。cueは具体的・短く。"
    "choiceのlabelは**キャラ名を付けず**、プレイヤーが取る行動を表す中立的な短い語句にすること"
    "(例『論理的に問い詰める』)。キャラ同士の対立などイベントでなく、必ず行動の選択肢にする。"
)

def validate(s):
    issues = []
    if not s.get("crisis"): issues.append("crisis欠落")
    beats = s.get("beats", [])
    if len(beats) != 7: issues.append(f"beats数={len(beats)}(7でない)")
    ch = [b for b in beats if b.get("kind") == "choice"]
    if len(ch) != 3: issues.append(f"choiceビート={len(ch)}(3でない)")
    for b in ch:
        if len(b.get("choices", [])) != 3: issues.append(f"beat{b.get('id')}の選択肢数≠3")
        labs = [c.get("label") for c in b.get("choices", [])]
        if len(set(labs)) < 3: issues.append(f"beat{b.get('id')}の選択肢が重複")
    d = s.get("dilemma", {})
    if not (d.get("A") and d.get("B")): issues.append("dilemmaのA/B欠落")
    if not s.get("ending_cue"): issues.append("ending_cue欠落")
    return issues

FIXED_CARD = {
    "id": 1, "title": "第一の事件・歪んだ記憶の断片",
    "logline": "近未来サイバーパンク都市。公安AI犯罪対策課のバディ捜査官リノン＆ルヴィアが、自律機械が起こした不可解な事件現場に臨場する。手口の解析中、犯行ログに『説明のつかない誰かの個人的な記憶の断片』が紛れているのを発見する。",
    "hook": "小さな事件だが、その記憶断片こそ、連続事件の背後にある『第三のAIの囚われた記憶』への最初の糸口。二人は捜査方針を選びながら、事件を決着させ手がかりを掴む。"
}

def main():
    print(f"[author] model={AUTHOR}（題材固定: 意識の在処）", flush=True)
    card = FIXED_CARD
    scen = chat(SCEN_SYS, f"この状況カードを台本設計図に展開して:\n{json.dumps(card, ensure_ascii=False)}", 2200)
    json.dump(scen, open(os.path.join(OUT, "scenario_01.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    iss = validate(scen)
    print(f"\n=== 展開シナリオ(card1) 検証: {'OK' if not iss else iss} ===", flush=True)
    print(f"title: {scen.get('title')}", flush=True)
    print(f"crisis: {scen.get('crisis')}", flush=True)
    for b in scen.get("beats", []):
        if b.get("kind") == "choice":
            print(f" beat{b.get('id')} [CHOICE] {b.get('prompt')}", flush=True)
            for c in b.get("choices", []):
                print(f"    - {c.get('label')} → {c.get('cue')}", flush=True)
        else:
            print(f" beat{b.get('id')} {b.get('cue')}", flush=True)
    d = scen.get("dilemma", {})
    print(f" 二択: {d.get('question')} / A={d.get('A')} / B={d.get('B')}", flush=True)
    print(f" 結末強制: {scen.get('ending_cue')}", flush=True)

if __name__ == "__main__":
    main()
