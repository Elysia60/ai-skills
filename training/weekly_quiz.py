# -*- coding: utf-8 -*-
"""weekly_quiz.py — 周一间隔重复抽题（2026-10-25 ZCode · 吸收方案 v2 基础设施）

学术地基：Roediger & Karpicke 2006（测试效应）+ Cepeda 2006（扩展间隔）。
机制：从 quiz_bank.json 随机抽 3 题（题面+出处指针，无答案明文）追加当日 daily；
幂等（当日已有 [周测抽题] 标记则跳过）；只写 daily 不做别的（P3-5）。
"""
import io
import json
import random
from datetime import date
from pathlib import Path

BANK = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\quiz_bank.json")
DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
MARK = "[周测抽题]"


def main() -> int:
    today = date.today().isoformat()
    f = DAILY / f"{today}.md"
    if not f.exists():
        # 2026-11-20 修：周测 09:00 跑在 DailyClosure(21:00) 之前，daily 天然还不存在——
        # 原实现直接 rc=2（WeeklyQuiz 11-16 红项根因）。改为先建当日文件骨架再抽题。
        DAILY.mkdir(parents=True, exist_ok=True)
        f.write_text(f"\n## [DSH-周测] {today}\n", encoding="utf-8")
        print(f"当日 daily 不存在，已建骨架: {f}")
    text = f.read_text(encoding="utf-8")
    if MARK in text:
        print("幂等：今日已抽题")
        return 0
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    picks = random.Random(today).sample(bank["questions"], 3)
    lines = [f"\n{MARK} 吸收方案v2·间隔重复（testing effect）——本周三题，答错回读对应族/条："]
    for i, q in enumerate(picks, 1):
        lines.append(f"  {i}. {q['q']}（出处：{q['ref']}）")
    lines.append("  （可选作答——主人令 token 经济：模型层/闸层已在替你学，动笔只为自证）")
    with io.open(f, "a", encoding="utf-8", newline="\n") as df:
        df.write("\n".join(lines) + "\n")
    print(f"已抽 {len(picks)} 题入 {today}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
