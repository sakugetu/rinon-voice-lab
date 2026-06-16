# -*- coding: utf-8 -*-
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
WS = "h:/RealTimeParallaxWindow/tasks/story_bench"
PICKS = {1: "1,2,3", 2: "3,1,2", 3: "2,3,1"}

for i in (1, 2, 3):
    src = os.path.join(ROOT, "out_play", f"play_0{i}.txt")
    out = [f"# ゲーム上演 play{i}「意識の在処」", "",
           f"選択の組み合わせ: `{PICKS[i]}` / 役者: Gemma-4-31B", ""]
    for ln in open(src, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if ln.startswith("# 危機"):
            out += ["> **危機**: " + ln.split(":", 1)[1].strip(), ""]
        elif ln.startswith("# "):
            continue
        elif ln.startswith("〈進行指示〉"):
            out += ["", "### ▶ " + ln.replace("〈進行指示〉", "").strip()]
        elif ln.startswith("★"):
            out += ["", "**🎮 " + ln.lstrip("★").strip() + "**", ""]
        elif ln.startswith("リノン:"):
            out.append("- **リノン**: " + ln.split(":", 1)[1].strip())
        elif ln.startswith("ルヴィア:"):
            out.append("- **ルヴィア**: " + ln.split(":", 1)[1].strip())
        elif ln.strip():
            out.append(ln)
    open(os.path.join(WS, f"game_play_0{i}.md"), "w", encoding="utf-8").write("\n".join(out))
print("wrote game_play_01..03.md")
