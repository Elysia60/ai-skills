# -*- coding: utf-8 -*-
"""distill_map_check.py — 蒸馏地图漂移检查器（2026-10-24 ZCode 建）

背景：蒸馏地图（文件地图/蒸馏地图-2026-10-24.md）维护规矩第 6 条"每次新增后更新本表"
      自己第一个没执行——patterns 12→13、总库 52→53，写完即漂。
教训（DSH 侧裁定）：任何索引/地图/登记表都是派生数据，必漂；对抗只有脚本生成。
用途：实测各层真实计数，与地图声明值对比，漂移即报。体检闸门，退出码 0=齐 1=漂。
用法：python distill_map_check.py [--map 路径]
状态：pending_verify —— 实现人 ZCode，验收人应为另一会话（maker≠checker）。
"""
import argparse
import io
import re
import sqlite3
import sys
from pathlib import Path

MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
DB = MEM / ".search-index.db"
PATTERNS = Path(r"D:\大肥鱼的深海\知识\patterns")
SKILL = MEM / "pending-skills" / "ledger-lessons" / "SKILL.md"
RAW84 = MEM / "工作经验教训84条-2026-10-24.md"


def actual() -> dict:
    a = {}
    # 手法层：SKILL.md 手法条数（节内的有序编号行）
    skill = SKILL.read_text(encoding="utf-8")
    body = skill.split("## 出师自测")[0]
    a["skill_methods"] = len(re.findall(r"^\d+\. \*\*", body, re.M))
    # 原料层：84 条合编的编号条数（顶层 x. 编号）
    raw = RAW84.read_text(encoding="utf-8")
    a["raw84_items"] = len(re.findall(r"^\d+\. \*\*", raw, re.M))
    a["patterns_count"] = len(list(PATTERNS.glob("*.md"))) if PATTERNS.exists() else -1
    if DB.exists():
        conn = sqlite3.connect(str(DB))
        a["index_files"] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
    else:
        a["index_files"] = -1
    return a


def declared(map_path: Path) -> dict:
    text = map_path.read_text(encoding="utf-8")
    d = {}
    m = re.search(r"八类\s*(\d+)\s*条", text)
    if m: d["skill_methods"] = int(m.group(1))
    m = re.search(r"(\d+)\s*条三档案合编", text)
    if m: d["raw84_items"] = int(m.group(1))
    m = re.search(r"patterns[/\s]*`?[^|]*?(\d+)\s*篇", text)
    if m: d["patterns_count"] = int(m.group(1))
    m = re.search(r"总库\s*(\d+)\s*文件", text)
    if m: d["index_files"] = int(m.group(1))
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(MEM / "文件地图" / "蒸馏地图-2026-10-24.md"))
    a = argparse.ArgumentParser
    args = ap.parse_args()
    mp = Path(args.map)
    if not mp.exists():
        print(f"✗ 蒸馏地图不存在: {mp}")
        return 2
    act, dec = actual(), declared(mp)
    print("== 蒸馏地图漂移检查 ==")
    drift = 0
    names = {"skill_methods": "手法层条数", "raw84_items": "84条合编", "patterns_count": "patterns 篇数", "index_files": "mem-search 总库"}
    for k, label in names.items():
        av, dv = act.get(k), dec.get(k)
        if dv is None:
            print(f"  · {label}: 实测 {av}（地图未声明——建议补声明）")
        elif av == dv:
            print(f"  ✓ {label}: {av} = 声明 {dv}")
        else:
            print(f"  ✗ {label}: 实测 {av} ≠ 声明 {dv} —— 地图漂移，需更新")
            drift += 1
    print("结论:", "✓ 无漂移" if drift == 0 else f"✗ {drift} 项漂移——规矩第 6 条：更新本表")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
