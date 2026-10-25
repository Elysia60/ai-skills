# -*- coding: utf-8 -*-
"""wed_scenario.py — 周三场景卡投递（吸收方案 v2 · 每周三 09:00）
从 scenario_cards.jsonl 随机抽 3 张追加当日 daily。
"""
import json
import random
from datetime import date
from pathlib import Path

CARDS = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\scenario_cards.jsonl")
DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
MARK = "[周三练习]"

today = date.today().isoformat()
f = DAILY / f"{today}.md"
if not f.exists():
    raise SystemExit(0)
text = f.read_text(encoding="utf-8")
if MARK in text:
    raise SystemExit(0)  # 幂等
cards = [json.loads(l) for l in CARDS.read_text(encoding="utf-8").splitlines() if l.strip()]
picks = random.Random(today).sample(cards, min(3, len(cards)))
lines = [f"\n{MARK} 场景卡练习（答错回读对应族/条）："]
for i, c in enumerate(picks, 1):
    lines.append(f"  {i}. {c['scenario'][:60]} → 验证：{c['verify'][:40]}")
with open(f, "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"周三场景卡 {len(picks)} 张已入 {today}.md")
