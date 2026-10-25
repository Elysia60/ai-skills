# -*- coding: utf-8 -*-
"""weekly_digest.py — 周报自动化（2026-10-25 ZCode · 巩固飞轮的可见层）

定位：夜间巩固攒教训（机器向）、周报给主人看（人向）——每周日 21:30，读近 7 天 daily，
产出 memories/周报-YYYY-WWn.md：本周教训数/验证状态/新增器官/闸趋势/下周看点。
规矩（P3-5）：只读 daily 与台账产物 + 写一个周报文件 + daily 一行；幂等。
用法：python weekly_digest.py
"""
import io
import re
from datetime import date, timedelta
from pathlib import Path

DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
MARK = "[周报]"


def main() -> int:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_tag = f"{monday.isocalendar().year}-W{monday.isocalendar().week:02d}"
    out = MEM / f"周报-{week_tag}.md"
    if out.exists():
        print("幂等：本周周报已生成")
        return 0
    files = [DAILY / f"{(monday + timedelta(days=i)).isoformat()}.md" for i in range(7)]
    lines_total, lesson_lines, zc_lines = 0, 0, 0
    new_things = []
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        lines_total += len(text.splitlines())
        lesson_lines += len(re.findall(r"修正|认领|抓到|教训|✗|根因|虚报|误判", text))
        zc_lines += len(re.findall(r"\[ZCode\]|\[DSH\]", text))
        for m in re.findall(r"【([^】]{4,30})】", text):
            new_things.append(m)
    digest = [
        f"# 周报 {week_tag}（{monday} ~ {monday + timedelta(days=6)}）",
        "",
        f"- 日记行数：{lines_total}（活跃条目 {zc_lines}）",
        f"- 教训/修正类关键词命中：{lesson_lines}（原料已由夜间巩固入队）",
        f"- 本周大事件（标题抽取）：",
    ]
    seen = set()
    for t in new_things:
        if t not in seen:
            seen.add(t)
            digest.append(f"  · {t}")
    digest += [
        "",
        "（验证状态/闸趋势：跑 `python verify_ledger.py` 与 `node ai-doctor.js organs` 取当刻值——周报不抄数字，防止抄旧数）",
        f"\n生成于 {today.isoformat()}（DSH WeeklyDigest 自动）",
    ]
    out.write_text("\n".join(digest), encoding="utf-8")
    today_file = DAILY / f"{today.isoformat()}.md"
    if today_file.exists():
        with io.open(today_file, "a", encoding="utf-8", newline="\n") as df:
            df.write(f"\n{MARK} {week_tag} 周报已生成 → {out.name}\n")
    print(f"周报生成: {out.name}（大事件 {len(seen)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
