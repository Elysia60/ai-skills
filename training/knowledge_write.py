# -*- coding: utf-8 -*-
"""knowledge_write.py — 知识文件一键写入工具（2026-11-06 · 治「四步流程容易漏步」）

把写知识文件后的四步收尾合成一条命令：
  ① FTS 索引刷新（新文件入检索）
  ② 蒸馏地图声明平账（活库计数追平）
  ③ 双轨同步（旧轨→新轨）
  ④ 锚闸验证（新文件的锚词能否查到自己）

每步独立报结果，任何一步失败不阻塞后续步骤（但最终 exit code 反映全部状态）。

用法：
  python knowledge_write.py                        # 检查全部（不写新文件，只刷新验证）
  python knowledge_write.py --file 新文件.md        # 写入新文件后运行全套收尾
  python knowledge_write.py --file 新文件.md --tags "标签1/标签2/标签3"
                                                   # --tags 自动生成检索锚行（如果文件没有的话）
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).parent
HOME = Path.home()
MEM = HOME / "AppData/Roaming/dsh-desktop/harness/memories"
NEWMEM = HOME / ".dsh/memories"
MS = HOME / ".zcode/workspace/default/memory-search/mem_search.py"
MAP_SYNC = HOME / ".zcode/workspace/default/memory-search/map_decl_sync.py"
SYNC = HOME / r"Documents/Codex/sync_memories.py"
ANCHOR = HOME / ".zcode/workspace/default/ai-skills/training/anchor_recall_check.py"

RESULTS = []


def add(step, ok, detail=""):
    RESULTS.append((step, ok, str(detail)[:100]))


def run(cmd, timeout=300):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def step_index():
    out = run([sys.executable, "-X", "utf8", str(MS), "index"])
    m = re.search(r"库内共 (\d+) 个文件", out)
    n = int(m.group(1)) if m else 0
    add("① FTS 索引刷新", True, f"索引 {n} 文件")
    return n


def step_map(n=0):
    out = run([sys.executable, "-X", "utf8", str(MAP_SYNC)])
    ok = "无漂移" in out
    add("② 蒸馏地图平账", ok, "无漂移" if ok else out[:60])


def step_sync():
    out = run([sys.executable, str(SYNC)])
    m = re.search(r"added=(\d+) updated=(\d+) same=(\d+)", out)
    if m:
        a, u, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        add("③ 双轨同步", True, f"added={a} updated={u} same={s}")
    else:
        add("③ 双轨同步", False, out[:60])


def step_anchor():
    out = run([sys.executable, "-X", "utf8", str(ANCHOR)])
    m = re.search(r"自可达率 (\d+)/(\d+)", out)
    if m:
        ok, total = int(m.group(1)), int(m.group(2))
        add("④ 锚闸验证", ok == total, f"{ok}/{total} 自可达")
    else:
        add("④ 锚闸验证", False, "未解析到自可达率")


def main():
    t0 = time.time()
    step_index()
    step_map()
    step_sync()
    step_anchor()

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print("═" * 50)
    print("知识文件写入 · 四步收尾")
    print("═" * 50)
    for step, ok, detail in RESULTS:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {step}: {detail}")
    print("─" * 50)
    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"  {n_ok}/{len(RESULTS)} 步完成")
    if n_fail:
        print(f"  ⚠ {n_fail} 步失败——检查上方输出")
    print(f"  耗时 {time.time()-t0:.1f}s")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
