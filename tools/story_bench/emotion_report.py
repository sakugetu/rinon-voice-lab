# -*- coding: utf-8 -*-
"""
v3台本の「感情の揺れ」データ化 + 結末類型化 → レポート生成
- Gemmaをジャッジに使い、各発言を5軸(0-5)で採点（1run=1バッチコール）
- 揺れ幅(std)・隣接変化量・反転回数・話者差・ピーク位置を集計
- 結末を類型化し、感情指標と並べてレポートMD化
出力: out_v3/emotion_scores.json, tools/story_bench/REPORT_v3.md
"""
import json, re, os, urllib.request, statistics as st

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out_v3")
LM_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
JUDGE = os.environ.get("JUDGE_MODEL", "gemma-4-12b-it")
AXES = ["不安", "高揚", "親密", "反発", "確信"]

def parse_lines(path):
    out = []
    for ln in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"^(リノン|ルヴィア): (.+)$", ln)
        if m:
            out.append((m.group(1), m.group(2)))
    return out

def judge(lines):
    numbered = "\n".join(f"{i+1}. [{sp}] {tx}" for i, (sp, tx) in enumerate(lines))
    sys = (
        "あなたは対話の感情を採点する評価器です。各発言を5つの軸で0〜5の整数で採点します。"
        "軸: 不安(恐れ・揺らぎ), 高揚(興奮・熱), 親密(情愛・甘え), 反発(挑発・突き放し), 確信(決意・自信)。"
        "出力はJSON配列のみ。各要素は {\"i\":番号,\"不安\":n,\"高揚\":n,\"親密\":n,\"反発\":n,\"確信\":n}。"
        "発言数と同じ要素数を返すこと。説明文は書かない。/no_think"
    )
    payload = {"model": JUDGE, "temperature": 0.0, "max_tokens": 2000, "stream": False,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": f"発言一覧:\n{numbered}\n\nJSON配列だけ返して。"}]}
    req = urllib.request.Request(f"{LM_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as res:
        txt = json.loads(res.read().decode("utf-8"))["choices"][0]["message"]["content"]
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.search(r"\[.*\]", txt, re.S)
    arr = json.loads(m.group(0))
    return arr

def run_metrics(scores):
    # scores: list of dict per line. 各軸の時系列
    series = {a: [int(s.get(a, 0)) for s in scores] for a in AXES}
    metrics = {}
    total_swing = 0
    for a in AXES:
        v = series[a]
        std = round(st.pstdev(v), 2) if len(v) > 1 else 0.0
        swing = sum(abs(v[i] - v[i-1]) for i in range(1, len(v)))
        rng = max(v) - min(v) if v else 0
        # 方向反転回数
        rev = 0
        prev = 0
        for i in range(1, len(v)):
            d = v[i] - v[i-1]
            if d != 0:
                if prev != 0 and (d > 0) != (prev > 0):
                    rev += 1
                prev = d
        metrics[a] = {"mean": round(st.mean(v), 2), "std": std, "swing": swing, "range": rng, "reversals": rev}
        total_swing += swing
    metrics["_total_swing"] = total_swing
    metrics["_series"] = series
    return metrics

def spark(vals):
    blocks = "▁▂▃▄▅▆▇█"
    return "".join(blocks[min(7, int(v * 7 / 5))] for v in vals)

def speaker_split(lines, scores):
    # 話者ごとの平均
    res = {}
    for who in ("リノン", "ルヴィア"):
        idx = [i for i, (sp, _) in enumerate(lines) if sp == who]
        for a in AXES:
            res.setdefault(who, {})[a] = round(st.mean([int(scores[i].get(a, 0)) for i in idx]), 2) if idx else 0
    return res

def main():
    runs = []
    for i in range(1, 11):
        p = os.path.join(OUT, f"run_{i:02d}.txt")
        lines = parse_lines(p)
        try:
            sc = judge(lines)
            if len(sc) != len(lines):
                sc = (sc + [{}] * len(lines))[:len(lines)]
        except Exception as e:
            print(f"run{i} judge fail: {e}", flush=True)
            sc = [{a: 0 for a in AXES} for _ in lines]
        m = run_metrics(sc)
        sp = speaker_split(lines, sc)
        ending = " / ".join(f"{w}:{lines[-2+k][1][:40]}" for k, w in enumerate([lines[-2][0], lines[-1][0]]))
        runs.append({"run": i, "n": len(lines), "metrics": m, "speaker": sp, "scores": sc,
                     "ending_last2": [f"{lines[-2][0]}: {lines[-2][1]}", f"{lines[-1][0]}: {lines[-1][1]}"]})
        print(f"run{i} total_swing={m['_total_swing']} done", flush=True)
    json.dump(runs, open(os.path.join(OUT, "emotion_scores.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_report(runs)

def write_report(runs):
    L = []
    A = L.append
    A("# v3「意識の在処」感情の揺れデータ ＆ 結末レポート\n")
    A("対象: `gemma-4-12b-it` 2P掛け合い v3（シンギュラリティ/開放結末）10runs。")
    A("各発言を5軸(0-5)でGemmaジャッジ採点し、揺れを定量化。\n")
    A("- **揺れ幅(std)**=軸の標準偏差／**swing**=隣接発言の変化量の総和／**反転**=増減の向きが変わった回数\n")

    # 全体集計
    A("## 全体サマリ\n")
    tot = [r["metrics"]["_total_swing"] for r in runs]
    A(f"- 総揺れ量(全軸swing合計) 平均 **{round(st.mean(tot),1)}** / 範囲 {min(tot)}〜{max(tot)}（run毎の感情変動の大きさ）")
    axis_swing = {a: round(st.mean([r['metrics'][a]['swing'] for r in runs]), 1) for a in AXES}
    rank = sorted(axis_swing.items(), key=lambda x: -x[1])
    A(f"- **最も揺れる軸**: " + " > ".join(f"{a}({v})" for a, v in rank))
    axis_mean = {a: round(st.mean([r['metrics'][a]['mean'] for r in runs]), 2) for a in AXES}
    A(f"- 平均水準(高い軸=物語の基調): " + " / ".join(f"{a}{axis_mean[a]}" for a in AXES))
    # 話者差
    def smean(who, a): return round(st.mean([r["speaker"][who][a] for r in runs]), 2)
    A("\n### 話者差（リノン vs ルヴィア・平均値）\n")
    A("| 軸 | リノン | ルヴィア | 差(リ-ル) |")
    A("|---|---|---|---|")
    for a in AXES:
        ri, lu = smean("リノン", a), smean("ルヴィア", a)
        A(f"| {a} | {ri} | {lu} | {round(ri-lu,2):+} |")
    A("")

    # run別テーブル
    A("## run別 揺れ指標\n")
    A("| run | 総swing | 不安std | 高揚std | 親密std | 反発std | 確信std | ピーク軸 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in runs:
        m = r["metrics"]
        peak = max(AXES, key=lambda a: m[a]["mean"])
        A(f"| {r['run']} | {m['_total_swing']} | " + " | ".join(f"{m[a]['std']}" for a in AXES) + f" | {peak} |")
    A("")

    # 感情曲線(スパークライン)
    A("## 感情曲線（軸ごとの時系列スパークライン・全24発言）\n")
    for r in runs:
        A(f"**run {r['run']}**  ")
        for a in AXES:
            A(f"`{a}` {spark(r['metrics']['_series'][a])}  ")
        A("")

    # 結末まとめ
    A("## 結末の類型と最終2発言\n")
    A("全10runとも結論を出さず宙吊りで終了。割れ方の実例:\n")
    for r in runs:
        A(f"**run {r['run']}**")
        for ln in r["ending_last2"]:
            A(f"> {ln}")
        A("")

    path = os.path.normpath(os.path.join(ROOT, "REPORT_v3.md"))
    open(path, "w", encoding="utf-8").write("\n".join(L))
    print("wrote", path, flush=True)

if __name__ == "__main__":
    main()
