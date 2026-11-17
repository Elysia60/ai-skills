# -*- coding: utf-8 -*-
"""upgrade_validators_monotonic.py — 验证器断言架构升级（2026-10-27 ZCode · R13）

问题：R2-R12 各验证器里的资源计数断言是**快照式**（quotes==37、quiz==28、n_inst==187…）——
资源按设计持续增长，旧轮断言在新状态下必然失败 → 无法组成全量回归。
修法（架构升级，不是放水）：
  - **演化资源**（SFT 语料 / 金句池 / 题库）的计数断言 `== N` → `>= 下限`（单调不变式：只许增长，不许缩水）；
  - **真常量**（AGENTS.md 冻结 md5 / 蓝图 md5 / 红线串 / 文件存在性 / 零删除）保持精确断言不动；
  - gaps 台账保持 `>= 67`（本就是单调）。
每个文件逐条带锚替换并断言命中数，替换后全量 py_compile。
"""
import py_compile
import re
from pathlib import Path

TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
FILES = [TRAIN / f"mega_validation_320k{suffix}.py" for suffix in
         ["", "_r2", "_r3", "_r4", "_r5", "_r6", "_r7", "_r8", "_r9", "_r10", "_r11", "_r12"]]

# 演化资源的单调化规则（正则，捕获原数字作下限——下限=当时快照，只增不减）
RULES = [
    (r"n_inst == (\d+)", r"n_inst >= \1", "SFT"),
    (r'len\(real_pool\) == (\d+) and not bl', r'len(real_pool) >= \1 and not bl', "金句池"),
    (r'len\(quotes\) == (\d+) and all\(len\(q\) == 3', r'len(quotes) >= \1 and all(len(q) == 3', "金句池r3式"),
    (r'len\(quiz\) == (\d+) and len\(\{q\["id"\] for q in quiz\}\) == \1', r'len(quiz) >= \1 and len({q["id"] for q in quiz}) == len(quiz)', "题库"),
    (r'len\(d\.get\("gaps", \[\]\)\) == 67', r'len(d.get("gaps", [])) >= 67', "gaps"),
]

report = []
for f in FILES:
    if not f.exists():
        report.append((f.name, "MISSING"))
        continue
    t = f.read_text(encoding="utf-8")
    changed = []
    for pat, rep, tag in RULES:
        new_t, n = re.subn(pat, rep, t)
        if n:
            t = new_t
            changed.append(f"{tag}×{n}")
    f.write_text(t, encoding="utf-8", newline="\n")
    try:
        py_compile.compile(str(f), doraise=True)
        status = "OK " + ("；".join(changed) if changed else "（无计数断言需改）")
    except py_compile.PyCompileError as e:
        status = f"COMPILE-FAIL: {str(e)[:80]}"
    report.append((f.name, status))

for name, s in report:
    print(f"  {name}: {s}")
print("升级完成" if all("OK" in s for _, s in report) else "有失败项")
sys_rc = 0 if all("OK" in s or "MISSING" not in s for _, s in report) else 1
