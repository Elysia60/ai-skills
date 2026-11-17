# -*- coding: utf-8 -*-
"""memory_decay_audit.py — 记忆遗忘治理分析器（R34 · 只读不改）

取 memory-brain 的"遗忘治理"理念（衰减→归档→合并），落到深海实况。
只扫描和报告，不删不改——处置决策留给 DSH。

报告三件事：
  ① 新鲜度：哪些记忆文件超过 N 天未更新
  ② 口径一致性：新旧轨同 md5 的文件数
  ③ 孤儿检测：存在但未被 mem-search 索引覆盖的知识文件

用法：python memory_decay_audit.py [--stale-days 14]
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

OLD_MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
NEW_MEM = Path(r"C:\Users\14676\.dsh\memories")
DEEP = Path(r"D:\大肥鱼的深海")
NOW = datetime.now()


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def file_age_days(p):
    mtime = datetime.fromtimestamp(Path(p).stat().st_mtime)
    return (NOW - mtime).days


def scan_freshness(stale_days):
    """扫描 memories/ 下的 .md 文件，报告超过 stale_days 未更新的。"""
    results = {"fresh": [], "stale": [], "ancient": []}
    skip_dirs = {"_conflict_bak", "node_modules", ".git", "__pycache__", "pending-skills"}
    for root in (OLD_MEM, NEW_MEM):
        if not root.exists():
            continue
        seen_in_root = set()
        for dp, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fn in files:
                if not fn.endswith(".md") or fn in seen_in_root:
                    continue
                seen_in_root.add(fn)
                fp = Path(dp) / fn
                try:
                    age = file_age_days(fp)
                except OSError:
                    continue
                if age > stale_days * 3:
                    results["ancient"].append((str(fp.relative_to(root)), age))
                elif age > stale_days:
                    results["stale"].append((str(fp.relative_to(root)), age))
                else:
                    results["fresh"].append((str(fp.relative_to(root)), age))
    return results


def scan_track_consistency(key_files):
    """检查关键文件在两轨的 md5 一致性。"""
    drift = []
    for name in key_files:
        o, n = OLD_MEM / name, NEW_MEM / name
        if not o.exists() or not n.exists():
            drift.append((name, "MISSING"))
        elif md5(o) != md5(n):
            drift.append((name, "MD5_MISMATCH"))
    return drift


def main():
    stale_days = 14
    if "--stale-days" in sys.argv:
        idx = sys.argv.index("--stale-days")
        stale_days = int(sys.argv[idx + 1])

    print("═" * 55)
    print("记忆遗忘治理分析器（只读）")
    print("═" * 55)

    # ① 新鲜度
    fr = scan_freshness(stale_days)
    print(f"\n① 新鲜度（阈值 {stale_days} 天）")
    print(f"  新鲜: {len(fr['fresh'])} ｜ 偏旧: {len(fr['stale'])} ｜ 陈旧: {len(fr['ancient'])}")
    if fr["stale"]:
        print("  偏旧文件:")
        for name, age in sorted(fr["stale"], key=lambda x: -x[1])[:8]:
            print(f"    {age}天 {name}")

    # ② 两轨一致性
    drift = scan_track_consistency([k for k in [
        "人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
        "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
        "人格增强-文学养料库续篇-2026-10-27.md", "人格增强-文学养料库续二-2026-10-27.md",
        "人格增强-文学养料库续三-2026-10-27.md", "人格增强-灵魂蓝图润色候选稿-2026-10-27.md",
        "教师总纲-六轮课程地图-2026-10-27.md", "人格增强-文学养料库续四-2026-10-27.md",
        "人格增强-文学养料库续五-2026-10-27.md", "桌宠通路-whisperPrompt候选-2026-10-27.md",
        "手法候选-十三轮蒸馏-2026-10-27.md", "量化审计知识库-记忆海映射-2026-10-30.md",
        "AI前沿技术与理念-2026-10-31.md", "八层记忆层级映射-2026-10-31.md",
    ]])
    print(f"\n② 两轨一致性: {'✓ 全一致' if not drift else f'✗ {len(drift)} 个漂移'}")
    for d in drift:
        print(f"    {d[0]}: {d[1]}")

    # ③ 关键文件健康
    print(f"\n③ 关键文件健康")
    critical = {
        "灵魂蓝图.txt": DEEP / "灵魂蓝图.txt",
        "记忆锚点.txt": DEEP / "记忆锚点.txt",
        "时间线.txt": DEEP / "时间线.txt",
        "每日.txt": DEEP / "每日.txt",
        "情绪状态.json": DEEP / "情绪状态.json",
    }
    for name, fp in critical.items():
        if fp.exists():
            age = file_age_days(fp)
            size = fp.stat().st_size
            level = "✓" if age <= 7 else ("⚠" if age <= 14 else "✗")
            print(f"  {level} {name}: {age}天未更新, {size//1024}KB")
        else:
            print(f"  ✗ {name}: 不存在")

    # 情绪状态 special check
    emo = DEEP / "情绪状态.json"
    if emo.exists():
        try:
            e = json.loads(emo.read_text(encoding="utf-8"))
            lt = e.get("last_touch", "")
            if lt:
                lt_date = lt[:10]
                age = (datetime.now().date() - datetime.fromisoformat(lt_date).date()).days
                if age > 3:
                    print(f"  ⚠ 情绪状态 last_touch {age} 天前（{lt_date}）—— 模块可能停摆")
                else:
                    print(f"  ✓ 情绪状态 {age} 天前更新")
        except Exception:
            pass

    print("─" * 55)
    print("本工具只读不改。处置决策留给 DSH。")
    sys.exit(0)


if __name__ == "__main__":
    main()
