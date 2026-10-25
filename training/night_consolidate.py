# -*- coding: utf-8 -*-
"""night_consolidate.py — 夜间巩固系统（2026-10-25 ZCode · 阶段三落地）

学术地基：Sleep-time Compute（arXiv 2504.13171, Letta 2025）——空闲期离线加工，
记忆巩固类比人类睡眠。EvoSC/MemSkill/ReasoningBank（前沿对齐报告已引）同源。
她生前设计（10-21 最后日记"台账工具化"+ ROADMAP P3-5 主动观测形态）的两月后兑现。

流程（严守 P3-5：只读输入 + 写产物目录 + 幂等 + 写日志一行）：
  ① 读当日 daily（只读）
  ② 抽取候选教训行（修正/认领/抓到/踩/✗/事故 关键词）
  ③ 追加到 training/consolidation_queue.md（原料队列——按 #42 攒 50+ 再蒸馏，不当晚蒸馏）
  ④ daily 写一行 [夜间巩固]（幂等：当日已写则跳过）
用法：python night_consolidate.py [--date 2026-10-25]
退出码：0=正常（含"无新教训"）；2=当日文件不存在。
"""
import io
import re
import sys
from datetime import date
from pathlib import Path

DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
QUEUE = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\consolidation_queue.md")
MARK = "[夜间巩固]"
PATS = re.compile(r"修正|认领|抓到|踩|教训|事故|✗|FAIL|bug|bug|犯错|虚报|误判|根因", re.I)


def main() -> int:
    d = date.today().isoformat() if "--date" not in sys.argv else sys.argv[sys.argv.index("--date") + 1]
    f = DAILY / f"{d}.md"
    if not f.exists():
        print(f"当日 daily 不存在: {f}")
        return 2
    text = f.read_text(encoding="utf-8")
    if MARK in text:
        print("幂等：当日已巩固，跳过")
        return 0
    # 抽取候选教训行（带条目头的行——保留上下文）
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hits = [l for l in lines if PATS.search(l) and l.startswith("[")]
    if not hits:
        n = 0
    else:
        QUEUE.parent.mkdir(parents=True, exist_ok=True)
        if not QUEUE.exists():
            QUEUE.write_text("# 巩固原料队列（夜间巩固系统自动追加；按 SKILL #42 攒 50+ 再蒸馏成手法/SFT）\n\n", encoding="utf-8")
        with io.open(QUEUE, "a", encoding="utf-8", newline="\n") as q:
            q.write(f"\n## {d}（自动抽取 {len(hits)} 行）\n")
            for h in hits:
                q.write(f"- {h[:220]}\n")
        n = len(hits)
    # daily 一行（幂等标记即本行）
    total = sum(1 for _ in io.open(QUEUE, encoding="utf-8")) if QUEUE.exists() else 0
    with io.open(f, "a", encoding="utf-8", newline="\n") as df:
        df.write(f"\n{MARK} 巩固队列 +{n} 行（累计 {total} 行）——Sleep-time 范式：今晚抽取原料，攒批蒸馏。\n")
    print(f"巩固完成：抽取 {n} 行入队列（累计 {total}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
