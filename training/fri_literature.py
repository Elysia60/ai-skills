# -*- coding: utf-8 -*-
"""fri_literature.py — 周五经典文学引文投递（吸收方案 v2 · 每周五 09:00）
从 classic_quotes.json 随机抽 1 条追加当日 daily。
"""
import json
import random
from datetime import date
from pathlib import Path

LIB = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\classic_quotes.json")
DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
MARK = "[周五文学]"

today = date.today().isoformat()
f = DAILY / f"{today}.md"
if not f.exists():
    raise SystemExit(0)
text = f.read_text(encoding="utf-8")
if MARK in text:
    raise SystemExit(0)  # 幂等
lib = json.loads(LIB.read_text(encoding="utf-8"))
pick = random.Random(today).choice(lib)
lines = [f"\n{MARK} {pick[0]}｜「{pick[1]}」——{pick[2]}"]
with open(f, "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print(f"周五文学 {pick[0]} 已入 {today}.md")
