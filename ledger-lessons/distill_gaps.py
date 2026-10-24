# -*- coding: utf-8 -*-
"""distill_gaps.py — 台账蒸馏标准工具（Skill-DisCo 管线的第一步，2026-10-24 ZCode）

用途：把 gaps.json 台账按状态分组蒸馏成结构化 markdown 骨架，
      供"轨迹→技能"（Trace2Skill 式）提炼起步，替代各 agent 手搓脚本。
用法：python distill_gaps.py [--status verified|open|pending_verify|all] [--out 路径]
      默认输出到 stdout；--status 缺省 verified（技能只从 verified 提炼——
      未闭环条目进 unfinished-business，不进技能）。
状态：pending_verify —— 实现人 ZCode，验收人应为另一会话（maker≠checker）。
"""
import argparse
import datetime as dt
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

GAPS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\gaps.json")
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


def load_items() -> list:
    g = json.loads(GAPS.read_text(encoding="utf-8"))
    return g if isinstance(g, list) else g.get("gaps", g.get("items", []))


def latest_date(text: str) -> str:
    dates = DATE_RE.findall(text or "")
    return max(dates) if dates else "无日期"


def distill(items: list, status_filter: str) -> str:
    now = dt.date.today().isoformat()
    groups = defaultdict(list)
    for it in items:
        st = str(it.get("status", "?"))
        if status_filter != "all" and st != status_filter:
            continue
        groups[st].append(it)
    out = [f"# 台账蒸馏 · {now}（status={status_filter}，{sum(len(v) for v in groups.values())} 条）",
           "",
           "> 本文件由 distill_gaps.py 自动生成——骨架供人工提炼「手法」后并入 SKILL.md。",
           "> 规矩：只从 verified 提炼技能；每条手法须回链台账 id（可 mem-search 回溯 evidence）。",
           ""]
    for st in ("verified", "pending_verify", "in_progress", "open", "closed"):
        if not groups.get(st):
            continue
        out.append(f"## {st}（{len(groups[st])} 条）")
        out.append("")
        for it in groups[st]:
            title = str(it.get("title", it.get("desc", ""))).replace("\n", " ")[:90]
            out.append(f"- **[{it.get('id','?')}]** {title} 〈最新证据 {latest_date(str(it.get('evidence','')))}〉")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="gaps.json 台账蒸馏骨架生成器")
    ap.add_argument("--status", default="verified",
                    choices=["verified", "open", "pending_verify", "in_progress", "closed", "all"])
    ap.add_argument("--out", default=None, help="输出文件路径（缺省 stdout）")
    a = ap.parse_args()
    text = distill(load_items(), a.status)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"已写入 {a.out}")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
